import asyncio
import logging
import threading
from typing import AsyncIterator
import Pyro4
import Pyro4.errors
from interface import RPCImplementation

# Prefix for Pyro name server registrations
PYRO_NS_PREFIX = "example.benchmark"

@Pyro4.expose
class BenchmarkService:
    """
    Pyro4 service implementation for benchmarking.
    This class is exposed to remote calls.
    """
    def simple_call(self, value):
        """Simple RPC call that doubles the input value"""
        return value * 2

    def stream_values(self, count):
        """
        Generator that yields values from 0 to count-1.
        Pyro4 can serialize generators and return them to clients.
        """
        for i in range(count):
            yield i


class PyroImplementation(RPCImplementation):
    """
    Implementation of the RPCImplementation interface using Pyro4.
    """
    def __init__(self, host='localhost', port=0, external_server=False, object_name=None):
        self.host = host
        self.port = port
        self.external_server = external_server
        self.object_name = object_name or f"{PYRO_NS_PREFIX}.benchmark"
        self.daemon = None
        self.server_thread = None
        self.proxy = None
        self.ns = None
        self._shutdown_event = threading.Event()  # Add shutdown event for clean termination

    async def setup(self):
        """
        Set up the Pyro4 implementation.
        If external_server is False, starts a daemon in a separate thread.
        Otherwise, connects to an existing server.
        """
        loop = asyncio.get_running_loop()

        # Use a queue for the daemon thread to signal readiness and pass URI/error
        self._shutdown_event.clear()  # Ensure event is clear before starting thread
        daemon_ready_queue = asyncio.Queue(maxsize=1)

        if not self.external_server:
            # Start our own daemon
            def start_daemon():
                try:
                    logging.debug("Daemon thread: Creating Pyro4.Daemon...")
                    # Create daemon
                    self.daemon = Pyro4.Daemon(host=self.host, port=self.port)
                    # Create and register an INSTANCE of the service
                    service_instance = BenchmarkService()
                    uri = self.daemon.register(service_instance)
                    logging.info(f"Pyro service registered locally at: {uri}")
                    
                    # No need to interact with NS when running in the same process.
                    # The direct URI is passed via the queue.
                    
                    # Signal readiness and provide the URI
                    loop.call_soon_threadsafe(daemon_ready_queue.put_nowait, {"uri": uri, "error": None})
                    
                    # Start the request loop, checking the shutdown event
                    logging.info("Pyro daemon starting request loop...")
                    self.daemon.requestLoop(lambda: not self._shutdown_event.is_set())
                    logging.info("Pyro daemon request loop finished.")
                except Exception as e:
                    logging.error(f"Error in Pyro daemon thread: {e}")
                    # Signal failure
                    loop.call_soon_threadsafe(daemon_ready_queue.put_nowait, {"uri": None, "error": e})

            # Start the daemon in a separate thread
            self.server_thread = threading.Thread(target=start_daemon, daemon=True)
            self.server_thread.start()
            
            # Wait for the daemon thread to signal readiness or failure
            try:
                result = await asyncio.wait_for(daemon_ready_queue.get(), timeout=10.0) # Wait up to 10s
            except asyncio.TimeoutError:
                raise TimeoutError("Pyro daemon did not become ready in time.")

            if result["error"]:
                raise RuntimeError(f"Pyro daemon failed to start: {result['error']}")
            
            daemon_uri = result["uri"]
            if not daemon_uri:
                raise RuntimeError("Pyro daemon started but did not provide a valid URI.")

            # Connect directly to the daemon using the obtained URI
            def connect():
                try:
                    logging.info(f"Connecting internal proxy directly to {daemon_uri}")
                    self.proxy = Pyro4.Proxy(daemon_uri)
                    # Test the connection
                    self.proxy._pyroBind()
                except Exception as e:
                    logging.error(f"Error connecting to Pyro service: {e}")
                    raise
            
            await loop.run_in_executor(None, connect)
        else:
            # Connect to external server
            def connect_to_external():
                try:
                    # Connect via name server
                    self.ns = Pyro4.locateNS()
                    uri = self.ns.lookup(self.object_name)
                    self.proxy = Pyro4.Proxy(uri)
                    
                    # Test the connection
                    self.proxy._pyroBind()
                except Exception as e:
                    logging.error(f"Error connecting to external Pyro service: {e}")
                    raise
            
            await loop.run_in_executor(None, connect_to_external)

    async def teardown(self):
        """Clean up resources"""
        if self.proxy:
            self.proxy._pyroRelease()
            self.proxy = None
        
        # Signal the daemon thread to stop and shut down the daemon
        if self.daemon:
            logging.info("Shutting down Pyro daemon...")
            self._shutdown_event.set()  # Signal loop to stop
            self.daemon.shutdown()
            self.daemon = None
        
        # Wait for the daemon thread to exit
        if self.server_thread:
            logging.info("Waiting for Pyro daemon thread to join...")
            self.server_thread.join(timeout=5.0)  # Increase join timeout
            if self.server_thread.is_alive():
                logging.warning("Pyro daemon thread did not exit cleanly after join timeout.")
            else:
                logging.info("Pyro daemon thread joined successfully.")
            self.server_thread = None

    async def simple_call(self, value) -> int:
        """Make a simple RPC call to double the value"""
        loop = asyncio.get_running_loop()
        
        def remote_call():
            try:
                return self.proxy.simple_call(value)
            except Exception as e:
                logging.error(f"Pyro simple_call error: {e}")
                raise
        
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, remote_call), 
                timeout=15.0
            )
            return result
        except asyncio.TimeoutError:
            logging.error("Pyro simple_call timeout")
            raise
        except Exception as e:
            logging.error(f"Pyro simple_call unexpected error: {e}")
            raise

    async def stream_values(self, count: int) -> AsyncIterator[int]:
        """Stream values from the remote generator"""
        loop = asyncio.get_running_loop()
        remote_iterator = None

        try:
            # Get the remote iterator object itself (synchronous Pyro call)
            def get_iterator():
                return self.proxy.stream_values(count)
                
            remote_iterator = await loop.run_in_executor(None, get_iterator)

            # Define an async generator that wraps the synchronous iteration
            async def iterate_remote():
                nonlocal remote_iterator
                try:
                    while True:
                        try:
                            # Get the next item - this blocks and needs the executor
                            def get_next():
                                try:
                                    return next(remote_iterator)
                                except StopIteration:
                                    return None
                                    
                            item = await loop.run_in_executor(None, get_next)
                            if item is None:  # StopIteration converted to None
                                break
                            yield item
                        except Exception as e:
                            logging.error(f"Error during Pyro stream iteration: {e}", exc_info=True)
                            break  # Stop on error
                finally:
                    # Ensure the remote iterator resources are released
                    if hasattr(remote_iterator, "_pyroRelease"):
                        try:
                            await loop.run_in_executor(None, remote_iterator._pyroRelease)
                            logging.debug("Pyro remote iterator released.")
                        except Exception as e:
                            logging.warning(f"Error releasing remote iterator: {e}")

            # Yield from the async generator wrapper
            async for item in iterate_remote():
                yield item

        except Exception as e:
            logging.error(f"Failed to initiate or iterate Pyro stream_values: {e}", exc_info=True)
            # Ensure cleanup even if initial call fails or during iteration error
            if remote_iterator and hasattr(remote_iterator, "_pyroRelease"):
                try:
                    await loop.run_in_executor(None, remote_iterator._pyroRelease)
                except Exception as e_release:
                    logging.warning(f"Error releasing remote iterator after failure: {e_release}")
            raise  # Re-raise the exception
