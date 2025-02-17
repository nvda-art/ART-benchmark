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

def test_large_payload(benchmark, rpc_implementation):
    instance, loop = rpc_implementation
    logging.info("Starting test_large_payload with 1MB payload")
    payload = "x" * (1024 * 1024)  # 1 MB payload
    async def payload_call():
        return await instance.simple_call(payload)
    result = benchmark(lambda: loop.run_until_complete(payload_call()))
    logging.info("Finished test_large_payload, result payload length: %s", len(result))
    # Expect the payload to be duplicated by simple_call (e.g. string multiplication)
    assert len(result) == 2 * len(payload)
