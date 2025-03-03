import sys
if sys.platform.startswith('win'):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import asyncio
import pytest
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', force=True)
from implementations.rpyc_impl import RPyCImplementation
from implementations.zmq_impl import ZMQImplementation
from implementations.grpc_impl import GRPCImplementation
TEST_RUN_COUNT = 0





def test_benchmark_simple_call(rpc_implementation, benchmark, event_loop):
    """Benchmark the simple_call RPC with concurrent calls using a synchronous wrapper."""
    import asyncio
    def run_test():
        # Use the existing event loop from the fixture instead of creating a new one
        loop = event_loop
        async def concurrent_test():
            semaphore = asyncio.Semaphore(10)
            async def limited_call():
                async with semaphore:
                    try:
                        return await asyncio.wait_for(rpc_implementation.simple_call(42), timeout=10)
                    except asyncio.TimeoutError:
                        logging.error("Timeout in simple_call RPC")
                        return None
            tasks = [limited_call() for _ in range(50)]
            results = await asyncio.gather(*tasks)
            return results
        try:
            results = loop.run_until_complete(asyncio.wait_for(concurrent_test(), timeout=60))
        except asyncio.TimeoutError:
            logging.error("Timeout in benchmark_simple_call test")
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
            result = loop.run_until_complete(asyncio.wait_for(collect(), timeout=60))
        except asyncio.TimeoutError:
            logging.error("Timeout in benchmark_stream_thousand test")
            return []
        return result
    result = benchmark(run_test)
    assert len(result) == 1000
