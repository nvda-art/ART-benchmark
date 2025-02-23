#!/usr/bin/env python
import argparse
import logging
import time
import threading
import rpyc
from implementations.rpyc_impl import BenchmarkService

def run_server(port):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    # Create the RPyC server using BenchmarkService
    server = rpyc.ThreadedServer(BenchmarkService, port=port, protocol_config={"allow_public_attrs": True})
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    time.sleep(0.5)
    print("READY", flush=True)
    # Keep the server running indefinitely
    while True:
        time.sleep(3600)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18861, help="Port to bind the RPyC server")
    args = parser.parse_args()
    run_server(args.port)
