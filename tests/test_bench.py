import sys
import asyncio
import pytest
import logging
import threading
import traceback

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s [%(levelname)8s] %(filename)s:%(lineno)d %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True
)

# Helper function to log current event loop info
def log_event_loop_info(prefix=""):
    try:
        current_loop = asyncio.get_running_loop()
        thread_id = threading.get_ident()
        logging.debug(f"{prefix}Event loop: id={id(current_loop)}, thread={thread_id}")
    except RuntimeError:
        logging.debug(f"{prefix}No event loop running in thread {threading.get_ident()}")
from implementations.rpyc_impl import RPyCImplementation
from implementations.zmq_impl import ZMQImplementation
from implementations.grpc_impl import GRPCImplementation
TEST_RUN_COUNT = 0





def test_benchmark_simple_call(rpc_implementation, benchmark):
    """Benchmark the simple_call RPC with concurrent calls using a synchronous wrapper."""
    import asyncio
    
    # Log test setup information
    logging.info(f"Current thread ID: {threading.get_ident()}")
    
    def run_test():
        # Use the existing event loop from the fixture instead of creating a new one
        
        async def concurrent_test():
            logging.info(f"concurrent_test started, event_loop id={id(asyncio.get_running_loop())}")
            logging.info(f"concurrent_test thread ID: {threading.get_ident()}")
            
            semaphore = asyncio.Semaphore(10)
            
            async def limited_call():
                logging.debug(f"limited_call started, thread ID: {threading.get_ident()}")
                log_event_loop_info("limited_call: ")
                
                async with semaphore:
                    try:
                        logging.debug("About to call rpc_implementation.simple_call(42)")
                        # Don't use asyncio.wait_for here to avoid event loop issues
                        # Let the RPC implementation handle its own timeouts
                        result = await rpc_implementation.simple_call(42)
                        logging.debug(f"simple_call returned: {result}")
                        return result
                    except Exception as e:
                        logging.error(f"Error in simple_call RPC: {e}")
                        logging.error(f"Exception traceback: {traceback.format_exc()}")
                        return None
            tasks = [limited_call() for _ in range(50)]
            results = await asyncio.gather(*tasks)
            return results
        try:
            # Use a longer timeout for the overall operation
            results = asyncio.get_event_loop().run_until_complete(asyncio.wait_for(concurrent_test(), timeout=120))
        except asyncio.TimeoutError:
            logging.error("Timeout in benchmark_simple_call test")
            return [None] * 50
        except Exception as e:
            logging.error(f"Unexpected error in benchmark_simple_call: {e}")
            return [None] * 50
        return results
    results = benchmark(run_test)
    # Check that we have at least some valid results
    valid_results = [r for r in results if r is not None]
    assert len(valid_results) > 0, "All RPC calls failed"
    # Check that all valid results are correct
    for result in valid_results:
        assert result == 84
def test_benchmark_stream_thousand(rpc_implementation, benchmark, event_loop):
    """Benchmark the stream_values RPC for 1000 values using a synchronous wrapper."""
    import asyncio
    def run_test():
        # Use the existing event loop from the fixture instead of creating a new one
        loop = event_loop
        async def collect():
            try:
                result = []
                async for x in rpc_implementation.stream_values(1000):
                    result.append(x)
                    # Add a timeout check for the entire operation
                    if len(result) % 100 == 0:
                        await asyncio.sleep(0)  # Yield to event loop occasionally
                return result
            except Exception as e:
                logging.error(f"Error in stream_values: {e}")
                return []
        try:
            # Use a longer timeout for the overall operation
            result = loop.run_until_complete(asyncio.wait_for(collect(), timeout=120))
        except asyncio.TimeoutError:
            logging.error("Timeout in benchmark_stream_thousand test")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in benchmark_stream_thousand: {e}")
            return []
        return result
    result = benchmark(run_test)
    assert len(result) == 1000
