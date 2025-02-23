#!/usr/bin/env python
import argparse
import asyncio
import logging
import os
if not os.path.exists("proto/rpc_pb2.py"):
    import subprocess
    subprocess.run(["python", "build_protos.py"], check=True)
from implementations.grpc_impl import GRPCImplementation

async def run_server(port):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    impl = GRPCImplementation(port=port)
    await impl.setup()
    logging.info("READY")
    logging.info("Entering idle loop to keep the gRPC server running")
    await asyncio.Event().wait()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=50051, help="Port to bind the gRPC server")
    args = parser.parse_args()
    asyncio.run(run_server(args.port))
