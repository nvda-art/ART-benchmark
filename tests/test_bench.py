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



@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_simple_call(rpc_implementation):
    logging.info("Starting test_simple_call")
    result = await asyncio.wait_for(
        asyncio.shield(rpc_implementation.simple_call(42)),
        timeout=20
    )
    logging.info("Finished test_simple_call with result: %s", result)
    assert result == 84

@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_stream_thousand(rpc_implementation):
    logging.info("Starting test_stream_thousand")
    async def collect():
        return [x async for x in rpc_implementation.stream_values(1000)]
    result = await asyncio.wait_for(collect(), timeout=20)
    logging.info("Finished test_stream_thousand, received %s stream values", len(result))
    assert len(result) == 1000

def test_benchmark_simple_call(rpc_implementation, benchmark):
    """Benchmark the simple_call RPC using a synchronous wrapper."""
    import asyncio
    def run_test():
        # Create a new event loop to avoid conflicts with the async test loop.
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(rpc_implementation.simple_call(42))
        finally:
            loop.close()
        return result
    result = benchmark(run_test)
    assert result == 84
