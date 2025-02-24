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
async def test_large_payload(rpc_implementation):
    logging.info("Starting test_large_payload for multiple payload sizes")
    sizes = [1024, 10*1024, 100*1024, 1024*1024]
    results = []
    for size in sizes:
        payload = "x" * size
        logging.info("Testing payload size: %s bytes", size)
        result = await asyncio.wait_for(
            asyncio.shield(rpc_implementation.simple_call(payload)),
            timeout=20
        )
        logging.debug("Payload of %s bytes returned result with length %s", size, len(result))
        results.append((size, result))
    for size, res in results:
         logging.info("Finished test_large_payload for payload %s bytes, result payload length: %s", size, len(res))
         assert len(res) == 2 * size
