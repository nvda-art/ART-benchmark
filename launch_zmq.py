#!/usr/bin/env python
import argparse
import asyncio
import logging
import sys
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from implementations.zmq_impl import ZMQImplementation

async def run_server(port):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', stream=sys.stdout)
    impl = ZMQImplementation()
    # Override the endpoint with the dynamic port
    impl.simple_endpoint = f"tcp://127.0.0.1:{port}"
    await impl.setup()
    logging.info("READY")
    sys.stdout.flush()
    # Keep the server running indefinitely
    await asyncio.Event().wait()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5555, help="Port to bind the ZeroMQ simple server")
    args = parser.parse_args()
    asyncio.run(run_server(args.port))
