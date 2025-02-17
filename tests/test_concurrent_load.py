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

@pytest.fixture(params=[RPyCImplementation, ZMQImplementation, GRPCImplementation])
def rpc_implementation(request):
    instance = request.param()
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(instance.setup())
    yield (instance, loop)
    loop.run_until_complete(instance.teardown())
    loop.close()

def test_concurrent_simple_call(benchmark, rpc_implementation):
    instance, loop = rpc_implementation
    logging.info("Starting test_concurrent_simple_call")
    async def concurrent_call():
        tasks = [instance.simple_call(42) for _ in range(50)]
        return await asyncio.gather(*tasks)
    results = benchmark(lambda: loop.run_until_complete(concurrent_call()))
    logging.info("Finished test_concurrent_simple_call with results: %s", results)
    assert all(result == 84 for result in results)
