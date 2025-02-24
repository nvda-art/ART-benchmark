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





def test_benchmark_simple_call(rpc_implementation, benchmark):
    """Benchmark the simple_call RPC with concurrent calls using a synchronous wrapper."""
    import asyncio
    def run_test():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def concurrent_test():
            semaphore = asyncio.Semaphore(10)
            async def limited_call():
                async with semaphore:
                    return await rpc_implementation.simple_call(42)
            tasks = [limited_call() for _ in range(50)]
            results = await asyncio.gather(*tasks)
            return results
        try:
            results = loop.run_until_complete(concurrent_test())
        finally:
            loop.close()
        return results
    results = benchmark(run_test)
    for result in results:
        assert result == 84
def test_benchmark_stream_thousand(rpc_implementation, benchmark):
    """Benchmark the stream_values RPC for 1000 values using a synchronous wrapper."""
    import asyncio
    def run_test():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def collect():
            return [x async for x in rpc_implementation.stream_values(1000)]
        try:
            result = loop.run_until_complete(collect())
        finally:
            loop.close()
        return result
    result = benchmark(run_test)
    assert len(result) == 1000
