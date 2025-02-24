import sys
if sys.platform.startswith('win'):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import asyncio
import pytest
import logging
from implementations.rpyc_impl import RPyCImplementation
from implementations.zmq_impl import ZMQImplementation
from implementations.grpc_impl import GRPCImplementation
TEST_RUN_COUNT = 0


def test_benchmark_concurrent_simple_call(rpc_implementation, benchmark):
    import asyncio
    def run_test():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def concurrent_call():
            semaphore = asyncio.Semaphore(10)
            async def limited_call():
                async with semaphore:
                    return await rpc_implementation.simple_call(42)
            tasks = [limited_call() for _ in range(50)]
            return await asyncio.gather(*tasks)
        try:
            results = loop.run_until_complete(concurrent_call())
        finally:
            loop.close()
        return results
    results = benchmark(run_test)
    assert all(result == 84 for result in results)
