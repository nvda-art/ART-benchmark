#!/usr/bin/env python
import argparse
import asyncio
import logging
import sys
import signal
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from implementations.zmq_impl import ZMQImplementation

# Handle signals properly
def handle_signal(sig, frame):
    print("Received signal, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

async def run_server(port):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', stream=sys.stdout)
    impl = ZMQImplementation()
    # Override the endpoint with the dynamic port
    impl.simple_endpoint = f"tcp://127.0.0.1:{port}"
    await impl.setup()
    print("READY", flush=True)
    logging.info("ZMQ server is ready and waiting for connections")
    sys.stdout.flush()
    
    try:
        # Keep the server running indefinitely
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logging.info("Server task cancelled")
    finally:
        # Clean up resources
        await impl.teardown()
        logging.info("Server shutdown complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5555, help="Port to bind the ZeroMQ simple server")
    args = parser.parse_args()
    
    try:
        asyncio.run(run_server(args.port))
    except KeyboardInterrupt:
        print("Server stopped by user")
