import asyncio
import logging
import threading
import time
import uuid
from typing import AsyncIterator

import Pyro5.api
import Pyro5.errors

from interface import RPCImplementation

# Configure logging for this module
log = logging.getLogger(__name__)

# Prefix for Pyro5 name server registrations
PYRO5_NS_PREFIX = "example.benchmark.pyro5"


@Pyro5.api.expose
class BenchmarkService:
    """
    Pyro5 service implementation for benchmarking.
    This class is exposed to remote calls using @Pyro5.api.expose.
    """

    def simple_call(self, value):
        """Simple RPC call that doubles the input value"""
        # log.debug(f"Pyro5 simple_call received: {value}")
        return value * 2

    def stream_values(self, count):
        """
        Generator that yields values from 0 to count-1.
        Pyro5 handles generators and returns a stream proxy.
        """
        # log.debug(f"Pyro5 stream_values called with count: {count}")
        for i in range(count):
            yield i
        # log.debug(f"Pyro5 stream_values finished yielding for count: {count}")


class Pyro5Implementation(RPCImplementation):
    """
    Implementation of the RPCImplementation interface using Pyro5.
    """

    def __init__(self, host='localhost', port=0, external_server=False, object_name=None):
        self.host = host
        self.port = port
        self.external_server = external_server
        # Ensure a unique name if running multiple instances locally without external server
        instance_id = uuid.uuid4().hex[:8] if not external_server else ""
        self.object_name = object_name or f"{PYRO5_NS_PREFIX}.{instance_id}"
        self.daemon = None
        self.server_thread = None
        self.proxy = None
        self.ns = None
        self._shutdown_event = threading.Event()
        log.info(
            f"Pyro5Implementation initialized: external={external_server}, name={self.object_name}")
        # Optionally configure Pyro5 settings
        # Pyro5.config.COMMTIMEOUT = 5.0

    async def setup(self):
        """
        Set up the Pyro5 implementation.
        If external_server is False, starts a daemon in a separate thread.
        Otherwise, connects to an existing server via the Name Server.
        """
        log.info(f"Setting up Pyro5 (external={self.external_server})")
        loop = asyncio.get_running_loop()
        self._shutdown_event.clear()

        if not self.external_server:
            # Start our own daemon in-process
            daemon_ready_queue = asyncio.Queue(maxsize=1)

            def start_daemon():
                try:
                    log.debug("Daemon thread: Creating Pyro5.api.Daemon...")
                    # Create daemon
                    self.daemon = Pyro5.api.Daemon(
                        host=self.host, port=self.port)
                    log.info(
                        f"Pyro5 daemon created on {self.daemon.locationStr}")

                    # Create and register an INSTANCE of the service
                    service_instance = BenchmarkService()
                    uri = self.daemon.register(
                        service_instance, self.object_name) # Register the instance
                    log.info(
                        f"Pyro5 service instance registered locally as '{self.object_name}' at: {uri}")

                    # Signal readiness and provide the URI
                    loop.call_soon_threadsafe(daemon_ready_queue.put_nowait, {
                                              "uri": uri, "error": None})

                    # Start the request loop, checking the shutdown event
                    log.info("Pyro5 daemon starting request loop...")
                    self.daemon.requestLoop(
                        lambda: not self._shutdown_event.is_set())
                    log.info("Pyro5 daemon request loop finished.")
                except Exception as e:
                    # Log full traceback
                    log.exception("Error in Pyro5 daemon thread")
                    # Signal failure
                    loop.call_soon_threadsafe(daemon_ready_queue.put_nowait, {
                                              "uri": None, "error": e})
                finally:
                    log.debug("Daemon thread exiting.")
                    if self.daemon:
                        self.daemon.close()  # Ensure daemon resources are cleaned up

            # Start the daemon in a separate thread
            self.server_thread = threading.Thread(
                target=start_daemon, name=f"Pyro5Daemon-{self.object_name}", daemon=True)
            self.server_thread.start()
            log.debug(f"Daemon thread {self.server_thread.name} started.")

            # Wait for the daemon thread to signal readiness or failure
            try:
                log.debug("Waiting for daemon ready signal...")
                # Increased timeout
                result = await asyncio.wait_for(daemon_ready_queue.get(), timeout=15.0)
                log.debug(f"Received daemon signal: {result}")
            except asyncio.TimeoutError:
                log.error("Pyro5 daemon did not become ready in time.")
                # Attempt to clean up thread if possible
                if self.server_thread and self.server_thread.is_alive():
                    self._shutdown_event.set()  # Signal thread to stop
                    self.server_thread.join(timeout=1.0)
                raise TimeoutError(
                    "Pyro5 daemon did not become ready in time.")

            if result["error"]:
                # Wait briefly for thread to potentially finish after error
                if self.server_thread and self.server_thread.is_alive():
                    self.server_thread.join(timeout=1.0)
                raise RuntimeError(
                    f"Pyro5 daemon failed to start: {result['error']}")

            daemon_uri = result["uri"]
            if not daemon_uri:
                if self.server_thread and self.server_thread.is_alive():
                    self.server_thread.join(timeout=1.0)
                raise RuntimeError(
                    "Pyro5 daemon started but did not provide a valid URI.")

            # Connect directly to the daemon using the obtained URI
            def connect():
                try:
                    log.info(
                        f"Connecting internal proxy directly to {daemon_uri}")
                    self.proxy = Pyro5.api.Proxy(daemon_uri)
                    # Test the connection
                    self.proxy._pyroBind()
                    log.info("Internal proxy connected successfully.")
                except Exception:
                    log.exception(
                        f"Error connecting internal proxy to Pyro5 service at {daemon_uri}")
                    raise

            await loop.run_in_executor(None, connect)

        else:
            # Connect to external server via Name Server
            def connect_to_external():
                retries = 5
                for attempt in range(retries):
                    try:
                        log.info(
                            f"Attempting to locate Pyro5 Name Server (attempt {attempt+1}/{retries})...")
                        self.ns = Pyro5.api.locate_ns()
                        log.info(
                            f"Pyro5 Name Server located at: {self.ns._pyroUri}")
                        log.info(
                            f"Looking up object '{self.object_name}' in NS...")
                        uri = self.ns.lookup(self.object_name)
                        log.info(
                            f"Object '{self.object_name}' found at URI: {uri}")
                        self.proxy = Pyro5.api.Proxy(uri)

                        # Test the connection
                        log.info("Binding proxy to remote object...")
                        self.proxy._pyroBind()
                        log.info("Proxy bound successfully to external server.")
                        return  # Success
                    except Pyro5.errors.NamingError as e:
                        log.warning(
                            f"NamingError connecting to external Pyro5 service (attempt {attempt+1}): {e}")
                        if attempt == retries - 1:
                            log.error(
                                f"Failed to find object '{self.object_name}' in Name Server after {retries} attempts.")
                            raise
                        time.sleep(2)  # Wait before retrying lookup
                    except Pyro5.errors.CommunicationError as e:
                        log.warning(
                            f"CommunicationError connecting to external Pyro5 service (attempt {attempt+1}): {e}")
                        if attempt == retries - 1:
                            log.error(
                                f"Failed to connect to external Pyro5 service at {getattr(self.proxy, '_pyroUri', 'unknown URI')} after {retries} attempts.")
                            raise
                        time.sleep(2)  # Wait before retrying connection
                    except Exception:
                        log.exception(
                            f"Unexpected error connecting to external Pyro5 service (attempt {attempt+1})")
                        raise  # Re-raise unexpected errors immediately

            await loop.run_in_executor(None, connect_to_external)
        log.info("Pyro5 setup complete.")

    async def teardown(self):
        """Clean up resources"""
        log.info(f"Tearing down Pyro5 (external={self.external_server})")
        if self.proxy:
            try:
                self.proxy._pyroRelease()
                log.debug("Pyro5 proxy released.")
            except Exception as e:
                log.warning(f"Error releasing Pyro5 proxy: {e}")
            self.proxy = None

        # Signal the daemon thread to stop and shut down the daemon
        if not self.external_server and self.daemon:
            log.info("Shutting down internal Pyro5 daemon...")
            self._shutdown_event.set()  # Signal loop to stop
            # Daemon shutdown needs to happen from a different thread than the one running the loop
            if self.daemon:
                # Use run_in_executor to avoid blocking the async loop
                shutdown_task = asyncio.get_running_loop().run_in_executor(None,
                                                                           self.daemon.shutdown)
                try:
                    await asyncio.wait_for(shutdown_task, timeout=5.0)
                    log.info("Pyro5 daemon shutdown initiated.")
                except asyncio.TimeoutError:
                    log.warning(
                        "Timeout waiting for daemon shutdown initiation.")
                except Exception as e:
                    log.error(f"Error initiating daemon shutdown: {e}")
                self.daemon = None  # Clear reference after initiating shutdown

        # Wait for the daemon thread to exit
        if not self.external_server and self.server_thread:
            log.info("Waiting for Pyro5 daemon thread to join...")
            # Use run_in_executor for the join as well
            join_task = asyncio.get_running_loop().run_in_executor(
                None, self.server_thread.join, 5.0)  # 5 sec timeout
            try:
                # Slightly longer timeout for the await
                await asyncio.wait_for(join_task, timeout=6.0)
                if self.server_thread.is_alive():
                    log.warning(
                        "Pyro5 daemon thread did not exit cleanly after join timeout.")
                else:
                    log.info("Pyro5 daemon thread joined successfully.")
            except asyncio.TimeoutError:
                log.warning(
                    "Timeout waiting for Pyro5 daemon thread join task.")
            except Exception as e:
                log.error(f"Error waiting for daemon thread join: {e}")
            self.server_thread = None
        log.info("Pyro5 teardown complete.")

    async def simple_call(self, value) -> int:
        """Make a simple RPC call to double the value"""
        if not self.proxy:
            raise RuntimeError("Pyro5 proxy not connected.")
        loop = asyncio.get_running_loop()

        def remote_call():
            # Create a thread-local copy of the proxy for this call
            local_proxy = self.proxy.__copy__()
            try:
                # log.debug(f"Executing remote simple_call with value: {value}")
                result = local_proxy.simple_call(value)
                # log.debug(f"Received result from remote simple_call: {result}")
                return result
            except Pyro5.errors.CommunicationError as e:
                log.error(f"Pyro5 communication error during simple_call: {e}")
                # Consider attempting reconnect or raising specific error
                raise
            except Exception:
                # Log full traceback
                log.exception("Pyro5 simple_call unexpected error")
                raise

        try:
            # Increased timeout for potentially slower remote calls
            result = await asyncio.wait_for(
                loop.run_in_executor(None, remote_call),
                timeout=30.0
            )
            return result
        except asyncio.TimeoutError:
            log.error("Pyro5 simple_call timed out.")
            raise
        except Exception:
            # Error already logged in remote_call, re-raise
            raise

    async def stream_values(self, count: int) -> AsyncIterator[int]:
        """Stream values from the remote generator"""
        if not self.proxy:
            raise RuntimeError("Pyro5 proxy not connected.")
        loop = asyncio.get_running_loop()

        def _collect_stream_sync():
            # This function runs entirely in the executor thread
            local_proxy = self.proxy.__copy__() # Create a proxy copy for this thread
            remote_iterator = None
            collected_items = []
            try:
                log.debug(f"Requesting remote iterator for stream_values({count})")
                remote_iterator = local_proxy.stream_values(count)
                log.debug(f"Received remote iterator proxy: {type(remote_iterator)}")
                # Iterate and collect all items synchronously within this thread
                for item in remote_iterator:
                    collected_items.append(item)
                log.debug(f"Collected {len(collected_items)} items from stream.")
                return collected_items
            except Exception:
                log.exception("Error during synchronous stream collection")
                raise # Re-raise exception to be caught by the await call
            finally:
                # Ensure the remote iterator resources are released
                if remote_iterator and hasattr(remote_iterator, "close"):
                    log.debug("Closing remote iterator...")
                    try:
                        remote_iterator.close()
                        log.debug("Pyro5 remote iterator closed.")
                    except Exception as e_close:
                        log.warning(f"Error closing remote iterator: {e_close}")

        try:
            # Run the synchronous collection function in the executor
            all_items = await asyncio.wait_for(
                loop.run_in_executor(None, _collect_stream_sync),
                timeout=60.0 # Adjust timeout as needed for potentially long streams
            )
            # Yield the collected items from the async generator
            for item in all_items:
                yield item
        except asyncio.TimeoutError:
            log.error(f"Pyro5 stream_values timed out after waiting for collection.")
            raise
        except Exception as e:
            log.exception(f"Failed to collect Pyro5 stream_values: {e}")
            raise # Re-raise the exception
