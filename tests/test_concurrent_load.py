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


@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_concurrent_simple_call(rpc_implementation):
    logging.info("Starting test_concurrent_simple_call")
    async def concurrent_call():
        semaphore = asyncio.Semaphore(10)
        async def limited_call():
            async with semaphore:
                return await rpc_implementation.simple_call(42)
        tasks = [limited_call() for _ in range(50)]
        return await asyncio.gather(*tasks)
    results = await asyncio.wait_for(concurrent_call(), timeout=20)
    logging.info("Finished test_concurrent_simple_call with results: %s", results)
    assert all(result == 84 for result in results)
