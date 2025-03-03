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


def test_benchmark_concurrent_simple_call(rpc_implementation, benchmark, event_loop):
    import asyncio
    def run_test():
        # Use the existing event loop from the fixture instead of creating a new one
        loop = event_loop
        async def concurrent_call():
            semaphore = asyncio.Semaphore(10)
            async def limited_call():
                async with semaphore:
                    try:
                        return await asyncio.wait_for(rpc_implementation.simple_call(42), timeout=10)
                    except asyncio.TimeoutError:
                        logging.error("Timeout in concurrent simple_call RPC")
                        return None
                    except Exception as e:
                        logging.error(f"Error in concurrent simple_call: {e}")
                        return None
            tasks = [limited_call() for _ in range(50)]
            return await asyncio.gather(*tasks)
        try:
            results = loop.run_until_complete(asyncio.wait_for(concurrent_call(), timeout=60))
        except asyncio.TimeoutError:
            logging.error("Timeout in benchmark_concurrent_simple_call test")
            return [None] * 50
        return results
    results = benchmark(run_test)
    # Check that we have at least some valid results
    valid_results = [r for r in results if r is not None]
    assert len(valid_results) > 0, "All RPC calls failed"
    # Check that all valid results are correct
    for result in valid_results:
        assert result == 84
