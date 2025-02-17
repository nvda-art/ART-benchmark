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


def test_simple_call(benchmark, rpc_implementation):
    instance, loop = rpc_implementation
    logging.info("Starting test_simple_call")
    async def simple_call_benchmark():
        return await instance.simple_call(42)
    result = benchmark(lambda: loop.run_until_complete(simple_call_benchmark()))
    logging.info("Finished test_simple_call with result: %s", result)
    # Since simple_call multiplies input by 2, we expect 84 when input is 42.
    assert result == 84

def test_stream_thousand(benchmark, rpc_implementation):
    instance, loop = rpc_implementation
    logging.info("Starting test_stream_thousand")
    async def stream_benchmark():
        return [x async for x in instance.stream_values(1000)]
    result = benchmark(lambda: loop.run_until_complete(stream_benchmark()))
    logging.info("Finished test_stream_thousand, received %s stream values", len(result))
    assert len(result) == 1000
