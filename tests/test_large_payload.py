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


def test_large_payload(benchmark, rpc_implementation):
    logging.info("Starting test_large_payload for multiple payload sizes")
    sizes = [1024, 10*1024, 100*1024, 1024*1024]
    async def run():
        results = []
        for size in sizes:
            payload = "x" * size
            logging.info("Testing payload size: %s bytes", size)
            result = await asyncio.wait_for(
                asyncio.shield(rpc_implementation.simple_call(payload)),
                timeout=5
            )
            results.append((size, result))
        return results
    results = benchmark(lambda: asyncio.run(run()))
    for size, res in results:
         logging.info("Finished test_large_payload for payload %s bytes, result payload length: %s", size, len(res))
         assert len(res) == 2 * size
