#!/usr/bin/env python
import argparse
import logging
import time
import threading
import os
import uuid
import sys
import rpyc
from named_pipe_impl import BenchmarkService, NamedPipeServer

def run_server(pipe_name=None):
    if os.name != "nt":
        print("Named pipes are only supported on Windows")
        sys.exit(1)
        
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    
    if pipe_name is None:
        pipe_name = r"\\.\pipe\RPyC_{}".format(uuid.uuid4().hex)
        
    # Create the RPyC server using NamedPipeServer
    server = NamedPipeServer(
        BenchmarkService, 
        port=0, 
        protocol_config={"allow_public_attrs": True}
    )
    server.pipe_name = pipe_name
    
    print(f"Starting named pipe server on {pipe_name}")
    print("READY", flush=True)
    
    # Start the server (this will block)
    server.start()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipe-name", type=str, help="Named pipe path")
    args = parser.parse_args()
    run_server(args.pipe_name)
