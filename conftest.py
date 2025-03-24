import asyncio
import logging
import socket
import subprocess
import sys
import time
import os
import pytest
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s', force=True)


def pytest_addoption(parser):
    parser.addoption("--rpc", action="store", default="rpyc", 
                     choices=["rpyc", "zmq", "grpc", "named-pipe"],
                     help="Choose the RPC implementation to benchmark.")
    parser.addoption("--rpc-isolated", action="store_true", default=False,
                     help="Run the RPC server in an isolated process.")


def launch_and_wait(cmd, protocol):
    import time  # Ensure time module is available in this scope
    logging.info(f"Starting {protocol} server with command: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    start_time = time.time()
    ready = False
        
    # Windows-compatible approach for reading from stdout without blocking
    import msvcrt
    import os
    import time
        
    while time.time() - start_time < 30:  # Increased timeout to 30 seconds
        # Check if the process has exited
        if proc.poll() is not None:
            logging.error(f"{protocol} server exited prematurely with code {proc.returncode}")
            # Get any remaining output
            remaining_output = proc.stdout.read()
            if remaining_output:
                logging.error(f"Server output: {remaining_output}")
            raise Exception(f"{protocol} server failed to start")
            
        # Read from stdout without blocking
        line = proc.stdout.readline()
        if line:
            line = line.strip()
            logging.info(f"{protocol} server output: {line}")
            if "READY" in line:
                logging.info(f"{protocol} server is ready.")
                ready = True
                break
        else:
            # No data available, sleep briefly
            time.sleep(0.1)
    
    if not ready:
        proc.kill()
        raise Exception(f"{protocol} server did not become ready in time.")
    return proc


import pytest_asyncio

@pytest_asyncio.fixture
async def rpc_implementation(request):
    rpc_type = request.config.getoption("--rpc")
    isolated = request.config.getoption("--rpc-isolated")
    
    logging.info(f"Setting up {rpc_type} implementation (isolated={isolated})")

    if isolated:
        # Dynamic port assignment
        port = get_dynamic_port()
        if rpc_type == "rpyc":
            cmd = [sys.executable, "-u", "launch_rpyc.py", "--port", str(port)]
            proc = launch_and_wait(cmd, "RPyC")
            from implementations.rpyc_impl import RPyCImplementation
            impl = RPyCImplementation(host="localhost", port=port, external_server=True)
            def connect():
                import rpyc
                impl.conn = rpyc.connect(impl.host, impl.port)
            await asyncio.get_running_loop().run_in_executor(None, connect)
            yield impl
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        elif rpc_type == "named-pipe":
            if os.name != "nt":
                pytest.skip("Named pipes are only supported on Windows")
            import uuid
            pipe_name = r"\\.\pipe\RPyC_{}".format(uuid.uuid4().hex)
            cmd = [sys.executable, "-u", "launch_named_pipe.py", "--pipe-name", pipe_name]
            proc = launch_and_wait(cmd, "Named Pipe")
            from named_pipe_impl import NamedPipeImplementation
            impl = NamedPipeImplementation(external_server=True)
            impl.pipe_name = pipe_name
            await impl.setup()
            yield impl
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        elif rpc_type == "grpc":
            cmd = [sys.executable, "-u", "launch_grpc.py", "--port", str(port)]
            proc = launch_and_wait(cmd, "gRPC")
            from implementations.grpc_impl import GRPCImplementation
            impl = GRPCImplementation(port=port, external_server=True)
            await impl.setup()
            yield impl
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        elif rpc_type == "zmq":
            cmd = [sys.executable, "-u", "launch_zmq.py", "--port", str(port)]
            proc = launch_and_wait(cmd, "ZeroMQ")
            from implementations.zmq_impl import ZMQImplementation
            impl = ZMQImplementation(external_server=True)
            impl.simple_endpoint = f"tcp://127.0.0.1:{port}"
            await asyncio.sleep(0.1)
            yield impl
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
    else:
        if rpc_type == "rpyc":
            from implementations.rpyc_impl import RPyCImplementation
            impl = RPyCImplementation()
        elif rpc_type == "named-pipe":
            if os.name != "nt":
                pytest.skip("Named pipes are only supported on Windows")
            from named_pipe_impl import NamedPipeImplementation
            impl = NamedPipeImplementation()
        elif rpc_type == "zmq":
            from implementations.zmq_impl import ZMQImplementation
            impl = ZMQImplementation()
        elif rpc_type == "grpc":
            from implementations.grpc_impl import GRPCImplementation
            impl = GRPCImplementation()
        try:
            logging.info(f"Setting up {rpc_type} implementation in-process")
            await asyncio.wait_for(impl.setup(), timeout=15)
            logging.info(f"{rpc_type} implementation setup complete")
            yield impl
        except asyncio.TimeoutError:
            logging.error(f"Timeout while setting up {rpc_type} implementation")
            raise
        finally:
            logging.info(f"Tearing down {rpc_type} implementation")
            try:
                await asyncio.wait_for(impl.teardown(), timeout=10)
            except Exception as e:
                logging.error(f"Error during teardown of {rpc_type}: {e}")

def get_dynamic_port():
    sock = socket.socket()
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port
