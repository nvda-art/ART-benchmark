import asyncio
import logging
import threading
import time
import uuid

import zmq
import zmq.asyncio
from interface import RPCImplementation

# Configure module logger
logger = logging.getLogger(__name__)


class ZMQImplementation(RPCImplementation):
    def __init__(self, external_server=False):
        logger.info(
            "Initializing ZMQImplementation (external_server=%s)", external_server)
        self.server_ctx = zmq.asyncio.Context()  # Context for server operations
        self.client_ctx = zmq.asyncio.Context()  # Separate context for client operations
        self.external_server = external_server
        
        # Use different ports for simple calls and streaming
        self.simple_endpoint = "tcp://127.0.0.1:5555"
        self.stream_endpoint = "tcp://127.0.0.1:5556"
        
        self.simple_server_task = None
        self.stream_server_task = None
        self.simple_server_ready = asyncio.Event()  # Event for simple server readiness
        self.stream_server_ready = asyncio.Event()  # Event for stream server readiness
        
        # Shared client socket for all simple_call operations
        self.client_socket = None
        self.client_socket_lock = asyncio.Lock()  # Lock for thread safety

        # REMOVED Shared client socket for stream_values operations
        # self.stream_client_socket = None
        # self.stream_client_socket_lock = None

        logger.debug("ZMQ simple endpoint: %s", self.simple_endpoint)
        logger.debug("ZMQ stream endpoint: %s", self.stream_endpoint)

    async def setup(self):
        logger.info("Setting up ZMQ implementation")
        if not self.external_server:
            # Start both servers
            self.simple_server_task = asyncio.create_task(
                self.run_simple_server())
            self.stream_server_task = asyncio.create_task(
                self.run_stream_server())
            
            try:
                # Wait for both servers to signal they're ready
                await asyncio.wait_for(self.simple_server_ready.wait(), timeout=5.0)
                await asyncio.wait_for(self.stream_server_ready.wait(), timeout=5.0)
                logger.info("ZMQ servers are ready.")
                
                # Create shared client socket for simple calls
                self.client_socket = self.client_ctx.socket(zmq.DEALER)
                self.client_socket.setsockopt(zmq.IDENTITY, b"client-shared-socket")
                self.client_socket.setsockopt(zmq.LINGER, 1000)  # Longer linger time
                self.client_socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
                self.client_socket.connect(self.simple_endpoint)
                logger.info("Created shared client socket")

                # REMOVED Creation of shared stream client socket

                # Test basic communication with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        result = await asyncio.wait_for(
                            self.test_basic_communication(),
                            timeout=5.0
                        )
                        if result:
                            logger.info("Basic ZMQ communication test passed")
                            break
                        else:
                            logger.warning(f"Basic ZMQ communication test failed (attempt {attempt+1}/{max_retries})")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(1)  # Wait before retry
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout in basic communication test (attempt {attempt+1}/{max_retries})")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)  # Wait before retry
                    except Exception as e:
                        logger.error(f"Error in basic communication test: {e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)  # Wait before retry
                        else:
                            raise
                else:
                    # This runs if the for loop completes without a break
                    logger.error("All basic ZMQ communication test attempts failed")
                    raise RuntimeError("Failed to establish basic ZMQ communication")
                    
            except asyncio.TimeoutError:
                logger.error("ZMQ servers did not become ready in time.")
                raise RuntimeError("ZMQ servers failed to start")

    async def teardown(self):
        logger.info("Tearing down ZMQ implementation")

        # Close the shared client socket first
        if self.client_socket and not self.client_socket.closed:
            try:
                self.client_socket.close()
                logger.info("Closed shared client socket")
            except Exception as e:
                logger.error(f"Error closing shared client socket: {e}")

        # REMOVED Closing of shared stream client socket

        # Cancel server tasks if running internally
        if not self.external_server:
            if self.simple_server_task:
                self.simple_server_task.cancel()
                try:
                    await self.simple_server_task
                except asyncio.CancelledError:
                    logger.info("ZMQ simple server task successfully cancelled.")
                    pass
                    
            if self.stream_server_task:
                self.stream_server_task.cancel()
                try:
                    await self.stream_server_task
                except asyncio.CancelledError:
                    logger.info("ZMQ stream server task successfully cancelled.")
                    pass

        # Allow time for sockets to close before terminating contexts
        await asyncio.sleep(0.2)  # Increased sleep time
        try:
            # Force garbage collection to help close any lingering sockets
            import gc
            gc.collect()
            
            if not self.server_ctx.closed:
                self.server_ctx.term()
            if not self.client_ctx.closed:
                self.client_ctx.term()
        except Exception as e:
            logger.error("Error during ZMQ context termination: %s", e)

    async def test_basic_communication(self):
        """Test basic ZMQ communication to verify the server is working."""
        logger.info("TESTING BASIC COMMUNICATION")
        
        # Test 1: Simple test message
        client_socket = self.client_ctx.socket(zmq.DEALER)
        client_socket.setsockopt(zmq.IDENTITY, b"test-basic-comm")  # Explicit identity
        client_socket.setsockopt(zmq.LINGER, 500)
        client_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        client_socket.connect(self.simple_endpoint)
        
        # Send a simple test message
        test_message = b'{"test": true}'
        logger.info(f"CLIENT: Sending test message: {test_message}")
        await client_socket.send_multipart([b"", test_message])
        logger.info("CLIENT: Test message sent")
        
        # Wait for response
        try:
            logger.info("CLIENT: Waiting for response")
            # Yield control to event loop before waiting for response
            await asyncio.sleep(0)
            _, response = await asyncio.wait_for(client_socket.recv_multipart(), timeout=5.0)
            logger.info(f"CLIENT: Received response: {response}")
            client_socket.close()
            
            # Test 2: Stream message
            stream_socket = self.client_ctx.socket(zmq.DEALER)
            stream_socket.setsockopt(zmq.IDENTITY, b"test-stream-comm")
            stream_socket.setsockopt(zmq.LINGER, 500)
            stream_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            stream_socket.connect(self.stream_endpoint)
            
            stream_message = zmq.utils.jsonapi.dumps({"count": 1, "request_id": "test-stream"})
            logger.info(f"CLIENT: Sending stream test message: {stream_message}")
            await stream_socket.send_multipart([b"", stream_message])
            logger.info("CLIENT: Stream test message sent")
            
            # Yield control to event loop before waiting for response
            await asyncio.sleep(0)
            
            try:
                logger.info("CLIENT: Waiting for stream response")
                _, stream_response = await asyncio.wait_for(stream_socket.recv_multipart(), timeout=5.0)
                logger.info(f"CLIENT: Received stream response: {stream_response}")
                return True
            except asyncio.TimeoutError:
                logger.error("CLIENT: Timeout waiting for stream response")
                return False
            finally:
                stream_socket.close()
        except asyncio.TimeoutError:
            logger.error("CLIENT: Timeout waiting for response")
            return False
        finally:
            if not client_socket.closed:
                client_socket.close()
    
    async def run_simple_server(self):
        """Runs a ROUTER socket server that handles simple calls only."""
        loop_id = id(asyncio.get_running_loop())
        logger.info("Starting ZMQ ROUTER server for simple calls on %s (event loop: %d)", self.simple_endpoint, loop_id)
        socket = self.server_ctx.socket(zmq.ROUTER)
        socket.setsockopt(zmq.LINGER, 0)  # Ensure immediate close when needed
        socket.bind(self.simple_endpoint)
        
        # Signal readiness after binding
        await asyncio.sleep(0.1)  # Give more time for binding to complete
        self.simple_server_ready.set()  # Signal that the server is ready
        logger.info("ZMQ simple server bound and ready event set.")

        try:  # Main server loop
            while True:
                try:
                    # This is already non-blocking with zmq.asyncio
                    # Add a timeout to prevent blocking forever
                    multipart = await asyncio.wait_for(
                        socket.recv_multipart(),
                        timeout=1.0  # 1 second timeout to allow for clean cancellation
                    )
                    
                    if len(multipart) != 3:
                        continue
                    
                    identity, empty, message = multipart

                    # <<< ADD YIELD HERE >>>
                    await asyncio.sleep(0) # Yield after receiving before processing

                    try:
                        msg = zmq.utils.jsonapi.loads(message)
                    except Exception:
                        error_response = zmq.utils.jsonapi.dumps({"error": "Invalid JSON format"})
                        await socket.send_multipart([identity, b"", error_response])
                        await asyncio.sleep(0) # Yield after sending error response
                        continue
                except asyncio.TimeoutError:
                    # This is just a timeout on the recv_multipart to allow for clean cancellation
                    # Just continue the loop
                    continue
                except asyncio.CancelledError:
                    raise
                except Exception:
                    await asyncio.sleep(0) # Yield on exception
                    # Continue the loop to keep the server running
                    continue

                # Handle test message
                if "test" in msg and msg["test"] is True:
                    response = zmq.utils.jsonapi.dumps({"test_response": True})
                    await socket.send_multipart([identity, b"", response])
                    await asyncio.sleep(0) # Yield after sending test response
                    continue

                # Process simple call
                if "value" in msg:  # Simple call
                    value = msg["value"]
                    if isinstance(value, str):
                        # Handle large payload test
                        result = value + value
                    else:
                        # Handle numeric value
                        result = value * 2

                    response = zmq.utils.jsonapi.dumps({"result": result})
                    await socket.send_multipart([identity, b"", response])
                    await asyncio.sleep(0) # Yield after sending simple call response
                else:
                    error_response = zmq.utils.jsonapi.dumps(
                        {"error": "Unknown request format"})
                    await socket.send_multipart([identity, b"", error_response])
                    await asyncio.sleep(0) # Yield after sending unknown format error
        except asyncio.CancelledError:
            logger.info("ZMQ simple server task cancelled.")
        except Exception as e:
            logger.error("ZMQ simple server error: %s", e, exc_info=True)
        finally:
            self.simple_server_ready.clear()  # Clear readiness on exit
            socket.setsockopt(zmq.LINGER, 0)  # Ensure immediate close
            socket.close()
            
    async def run_stream_server(self):
        """Runs a ROUTER socket server that handles streaming only."""
        loop_id = id(asyncio.get_running_loop())
        logger.info("Starting ZMQ ROUTER server for streaming on %s (event loop: %d)", self.stream_endpoint, loop_id)
        socket = self.server_ctx.socket(zmq.ROUTER)
        socket.setsockopt(zmq.LINGER, 0)  # Ensure immediate close when needed
        socket.bind(self.stream_endpoint)
        
        # Signal readiness after binding
        await asyncio.sleep(0.1)  # Give more time for binding to complete
        self.stream_server_ready.set()  # Signal that the server is ready
        logger.info("ZMQ stream server bound and ready event set.")

        # Simple state tracking for streams
        streams = {}

        try:  # Main server loop
            while True:
                try:
                    # This is already non-blocking with zmq.asyncio
                    # Add a timeout to prevent blocking forever
                    multipart = await asyncio.wait_for(
                        socket.recv_multipart(),
                        timeout=1.0  # 1 second timeout to allow for clean cancellation
                    )
                    
                    # Log the raw bytes received
                    logger.debug("STREAM SERVER: Received multipart message with %d parts", len(multipart))
                    
                    if len(multipart) != 3:
                        logger.error("STREAM SERVER: Invalid message format (expected 3 parts, got %d)", len(multipart))
                        continue
                    
                    identity, empty, message = multipart
                    logger.debug("STREAM SERVER: Message from identity: %r", identity)

                    # <<< ADD YIELD HERE >>>
                    await asyncio.sleep(0) # Yield after receiving before processing

                    try:
                        msg = zmq.utils.jsonapi.loads(message)
                        logger.debug("STREAM SERVER: Successfully parsed JSON message: %s", msg)
                    except Exception as e:
                        logger.error("STREAM SERVER: Failed to parse JSON message: %s. Error: %s", message, e)
                        error_response = zmq.utils.jsonapi.dumps({"error": "Invalid JSON format"})
                        await socket.send_multipart([identity, b"", error_response])
                        await asyncio.sleep(0) # Yield after sending error response
                        continue
                except asyncio.TimeoutError:
                    # This is just a timeout on the recv_multipart to allow for clean cancellation
                    # Just continue the loop
                    continue
                except asyncio.CancelledError:
                    logger.info("ZMQ stream server task cancelled during receive.")
                    raise
                except Exception as e:
                    logger.error("STREAM SERVER: Error receiving message: %s", e, exc_info=True)
                    await asyncio.sleep(0) # Yield on exception
                    # Continue the loop to keep the server running
                    continue

                # Handle test message
                if "test" in msg and msg["test"] is True:
                    logger.info("STREAM SERVER: Received test message, sending response")
                    response = zmq.utils.jsonapi.dumps({"test_response": True})
                    await socket.send_multipart([identity, b"", response])
                    await asyncio.sleep(0) # Yield after sending test response
                    continue

                # Process stream requests
                if "count" in msg:  # Initial stream request
                    logger.debug("STREAM SERVER: Processing stream request with count: %d", msg["count"])
                    count = msg["count"]
                    request_id = msg.get("request_id", str(uuid.uuid4()))
                    logger.debug("STREAM SERVER: Stream request_id: %s", request_id)

                    if count <= 0:
                        # Handle empty stream case
                        logger.debug("STREAM SERVER: Empty stream requested, sending None value")
                        await socket.send_multipart([identity, b"", zmq.utils.jsonapi.dumps({"value": None})])
                        continue

                    # Store stream state
                    streams[request_id] = {
                        "current": 0,
                        "count": count,
                        "identity": identity  # Store client identity for later responses
                    }
                    logger.debug("STREAM SERVER: Created stream state for req_id %s: %s", request_id, streams[request_id])

                    # Send first value
                    response = zmq.utils.jsonapi.dumps({"value": 0})
                    logger.debug("STREAM SERVER: Starting stream for req_id %s with %d items", request_id, count)
                    await socket.send_multipart([identity, b"", response])
                    logger.debug("STREAM SERVER: First stream value sent successfully for req_id %s", request_id)
                    await asyncio.sleep(0) # Yield after sending first value

                elif "next" in msg:  # Subsequent stream request
                    request_id = msg.get("request_id", "unknown")
                    logger.debug("STREAM SERVER: Processing 'next' request for stream req_id: %s", request_id)

                    if request_id not in streams:
                        logger.error("STREAM SERVER: Unknown stream request_id: %s. Available streams: %s", 
                                    request_id, list(streams.keys()))
                        error_response = zmq.utils.jsonapi.dumps(
                            {"error": "Unknown stream"})
                        await socket.send_multipart([identity, b"", error_response])
                        continue

                    stream = streams[request_id]
                    stream["current"] += 1
                    logger.debug("STREAM SERVER: Updated stream current value to %d", stream["current"])

                    if stream["current"] >= stream["count"]:
                        # Stream complete, clean up
                        logger.debug("STREAM SERVER: Stream completed for req_id %s, cleaning up", request_id)
                        del streams[request_id]

                    # Send next value
                    response = zmq.utils.jsonapi.dumps({"value": stream["current"]})
                    logger.debug("STREAM SERVER: Sending next stream value %d for req_id %s", 
                                stream["current"], request_id)
                    await socket.send_multipart([identity, b"", response])
                    logger.debug("STREAM SERVER: Next stream value sent successfully for req_id %s", request_id)
                    await asyncio.sleep(0) # Yield after sending next value

                else:
                    logger.error("STREAM SERVER: Unknown message format: %s", msg)
                    error_response = zmq.utils.jsonapi.dumps(
                        {"error": "Unknown request format"})
                    await socket.send_multipart([identity, b"", error_response])
                    await asyncio.sleep(0) # Yield after sending unknown format error
        except asyncio.CancelledError:
            logger.info("ZMQ stream server task cancelled.")
        except Exception as e:
            logger.error("ZMQ stream server error: %s", e, exc_info=True)
        finally:
            self.stream_server_ready.clear()  # Clear readiness on exit
            socket.setsockopt(zmq.LINGER, 0)  # Ensure immediate close
            socket.close()

    async def simple_call(self, value) -> object:
        loop_id = id(asyncio.get_running_loop())
        logger.debug("CLIENT: simple_call running in event loop %d", loop_id)
        TIMEOUT = 10.0  # 10 second timeout for socket operations

        try:
            # Use the shared socket with a lock for thread safety
            async with self.client_socket_lock:
                # Send request (empty delimiter frame + content)
                request = zmq.utils.jsonapi.dumps({"value": value})
                await self.client_socket.send_multipart([b"", request])

                # Wait for response with timeout
                try:
                    # Use asyncio.wait_for to enforce timeout at asyncio level
                    _, response = await asyncio.wait_for(
                        self.client_socket.recv_multipart(), 
                        timeout=TIMEOUT
                    )
                    response_data = zmq.utils.jsonapi.loads(response)
                except asyncio.TimeoutError:
                    raise RuntimeError(f"Timeout waiting for simple_call response after {TIMEOUT} seconds")

            return response_data["result"]
        except Exception as e:
            raise

    async def stream_values(self, count: int):
        thread_id = threading.get_ident()
        # Use a shorter request ID
        request_id = f"stream-{thread_id}"  # Much shorter than UUID
        logger.debug("CLIENT req_id %s: Requesting stream of %d values (thread: %d)",
                     request_id, count, thread_id)

        if count <= 0:
            logger.debug("CLIENT req_id %s: Empty stream requested, returning immediately", request_id)
            return

        # Log event loop ID
        loop_id = id(asyncio.get_running_loop())
        logger.debug("CLIENT req_id %s: stream_values running in event loop %d", request_id, loop_id)

        socket = None # Initialize local socket variable
        items_received = 0
        start_time = time.time()
        TIMEOUT = 15.0  # Increased timeout slightly for debugging

        try:
            # Create and connect a DEALER socket for this specific stream
            socket = self.client_ctx.socket(zmq.DEALER)
            # Use a unique identity for this stream's socket
            socket_identity = f"stream-{request_id}".encode()
            socket.setsockopt(zmq.IDENTITY, socket_identity)
            socket.setsockopt(zmq.LINGER, 0) # Close immediately if needed
            # DO NOT set RCVTIMEO here, rely on asyncio.wait_for
            socket.connect(self.stream_endpoint)
            logger.debug("CLIENT req_id %s: Created and connected dedicated socket with identity %r",
                         request_id, socket_identity)

            # Send initial request (empty delimiter frame + content)
            request = zmq.utils.jsonapi.dumps(
                {"count": count, "request_id": request_id})
            logger.debug("CLIENT req_id %s: Sending initial stream request", request_id)
            await socket.send_multipart([b"", request]) # Use local socket
            logger.debug("CLIENT req_id %s: Initial stream request sent successfully", request_id)

            # Receive first value with timeout
            logger.debug("CLIENT req_id %s: Waiting for first stream value (timeout: %ss)", request_id, TIMEOUT)
            try:
                # Use asyncio.wait_for to enforce timeout at asyncio level
                logger.debug("CLIENT req_id %s: Entering await socket.recv_multipart() for first value", request_id)
                raw_response = await asyncio.wait_for(
                    socket.recv_multipart(), # Use local socket
                    timeout=TIMEOUT
                )
                logger.debug("CLIENT req_id %s: Exited await socket.recv_multipart() for first value", request_id)
                # Expecting [empty, payload] from DEALER after ROUTER routes it
                if len(raw_response) != 2:
                     logger.error("CLIENT req_id %s: Received unexpected multipart message length: %d parts, content: %r",
                                  request_id, len(raw_response), raw_response)
                     raise RuntimeError(f"CLIENT req_id {request_id}: Unexpected response format from server.")
                _, response = raw_response
                logger.debug("CLIENT req_id %s: Received first response payload: %r", request_id, response)
            except asyncio.TimeoutError:
                logger.error("CLIENT req_id %s: asyncio.TimeoutError waiting for first stream value", request_id)
                raise RuntimeError(f"Timeout waiting for first stream value after {TIMEOUT} seconds")

            msg = zmq.utils.jsonapi.loads(response)
            logger.debug("CLIENT req_id %s: Parsed first response: %s", request_id, msg)

            if "error" in msg:
                logger.error("CLIENT req_id %s: Server returned error: %s", request_id, msg["error"])
                raise RuntimeError(
                    f"CLIENT req_id {request_id}: Error from server: {msg['error']}")

            if "value" not in msg:
                logger.error("CLIENT req_id %s: Invalid response format, missing 'value': %s", request_id, msg)
                raise RuntimeError(
                    f"CLIENT req_id {request_id}: Invalid response format: {msg}")

            # Yield first value
            logger.debug("CLIENT req_id %s: Yielding first value: %s", request_id, msg["value"])
            yield msg["value"]
            items_received += 1

            # Request and yield remaining values
            for i in range(1, count):
                # Send request for next value
                next_request = zmq.utils.jsonapi.dumps(
                    {"next": True, "request_id": request_id})
                logger.debug("CLIENT req_id %s: Sending request for next value (%d/%d)", 
                            request_id, i+1, count)
                # Use the dedicated stream socket
                await socket.send_multipart([b"", next_request])
                logger.debug("CLIENT req_id %s: Next request sent successfully", request_id)

                # Receive next value with timeout
                logger.debug("CLIENT req_id %s: Waiting for next value (%d/%d)", request_id, i+1, count)
                try:
                    # Use asyncio.wait_for to enforce timeout at asyncio level
                    # Use the dedicated stream socket
                    _, response = await asyncio.wait_for(
                        socket.recv_multipart(),
                        timeout=TIMEOUT
                    )
                    logger.debug("CLIENT req_id %s: Received next response for item %d", request_id, i+1)
                except asyncio.TimeoutError:
                    logger.error("CLIENT req_id %s: Timeout waiting for value %d", request_id, i+1)
                    raise RuntimeError(f"Timeout waiting for stream value {i+1} after {TIMEOUT} seconds")

                msg = zmq.utils.jsonapi.loads(response)
                logger.debug("CLIENT req_id %s: Parsed next response for item %d", request_id, i+1)

                if "error" in msg:
                    logger.error("CLIENT req_id %s: Server returned error for item %d: %s", 
                                request_id, i+1, msg["error"])
                    raise RuntimeError(
                        f"CLIENT req_id {request_id}: Error from server: {msg['error']}")

                if "value" not in msg:
                    logger.error("CLIENT req_id %s: Invalid response format for item %d: %s", 
                                request_id, i+1, msg)
                    raise RuntimeError(
                        f"CLIENT req_id {request_id}: Invalid response format: {msg}")

                logger.debug("CLIENT req_id %s: Yielding value %d: %s", request_id, i+1, msg["value"])
                yield msg["value"]
                items_received += 1

                # Log progress periodically
                if items_received % 100 == 0 or i == count-1:
                    elapsed = time.time() - start_time
                    rate = items_received / elapsed if elapsed > 0 else 0
                    logger.debug("CLIENT req_id %s: Received %d/%d values (%.1f items/sec)",
                                 request_id, items_received, count, rate)

            duration = time.time() - start_time
            logger.debug("CLIENT req_id %s: Completed receiving %d values in %.3f s",
                         request_id, count, duration)

        except Exception as e:
            logger.error(
                "CLIENT req_id %s: Error during stream_values: %s", request_id, e, exc_info=True)
            raise  # Re-raise after logging
        finally:
            # Ensure the dedicated socket is always closed
            if socket and not socket.closed:
                try:
                    socket.close(linger=0) # Close immediately
                    logger.debug(f"CLIENT req_id %s: Closed dedicated stream socket", request_id)
                except Exception as e:
                    logger.error(f"CLIENT req_id %s: Error closing stream socket: {e}", request_id)
