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



def test_simple_call(benchmark, rpc_implementation):
    logging.info("Starting test_simple_call")
    async def simple_call_benchmark():
        return await rpc_implementation.simple_call(42)
    async def run():
        return await asyncio.wait_for(asyncio.shield(simple_call_benchmark()), timeout=5)
    result = benchmark(lambda: asyncio.run(run()))
    logging.info("Finished test_simple_call with result: %s", result)
    assert result == 84

def test_stream_thousand(benchmark, rpc_implementation):
    logging.info("Starting test_stream_thousand")
    async def stream_benchmark():
        return [x async for x in rpc_implementation.stream_values(1000)]
    result = benchmark(lambda: asyncio.run(asyncio.wait_for(stream_benchmark(), timeout=5)))
    logging.info("Finished test_stream_thousand, received %s stream values", len(result))
    assert len(result) == 1000
