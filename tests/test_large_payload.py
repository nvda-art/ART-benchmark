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



def test_benchmark_large_payload(rpc_implementation, benchmark):
    """Benchmark the simple_call RPC for large payloads with concurrent calls."""
    import asyncio
    def run_test():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def concurrent_payload():
            sizes = [1024, 10*1024, 100*1024, 1024*1024]
            async def call_payload(size):
                payload = "x" * size
                result = await rpc_implementation.simple_call(payload)
                return (size, result)
            tasks = [call_payload(size) for size in sizes]
            results = await asyncio.gather(*tasks)
            return results
        try:
            results = loop.run_until_complete(concurrent_payload())
        finally:
            loop.close()
        return results
    results = benchmark(run_test)
    for size, res in results:
         assert len(res) == 2 * size
