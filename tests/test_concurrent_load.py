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


def test_concurrent_simple_call(benchmark, rpc_implementation):
    logging.info("Starting test_concurrent_simple_call")
    async def concurrent_call():
        tasks = [rpc_implementation.simple_call(42) for _ in range(50)]
        return await asyncio.gather(*tasks)
    async def run():
        return await asyncio.wait_for(asyncio.shield(concurrent_call()), timeout=5)
    results = benchmark(lambda: asyncio.run(run()))
    logging.info("Finished test_concurrent_simple_call with results: %s", results)
    assert all(result == 84 for result in results)
