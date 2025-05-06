import asyncio
import logging
import socket
import subprocess
import sys
import time
import os
import uuid
import pytest


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s', force=True)


def pytest_addoption(parser):
    parser.addoption("--rpc", action="store", default="rpyc",
                     choices=["pure-python", "rpyc", "zmq", "grpc", "named-pipe", "pyro", "pyro5"],
                     help="Choose the RPC implementation to benchmark.")
    parser.addoption("--rpc-isolated", action="store_true", default=False,
                     help="Run the RPC server in an isolated process (ignored for pure-python).")


async def launch_and_wait(cmd, protocol, timeout=30):
    logging.info(f"Starting {protocol} server with command: {' '.join(cmd)}")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT # Redirect stderr to stdout
    )

    ready = False
    output_lines = [] # Store output for debugging if needed
    try:
        async with asyncio.timeout(timeout):
            while True:
                try:
                    line_bytes = await proc.stdout.readline()
                    if not line_bytes: # EOF
                        logging.error(f"{protocol} server exited prematurely. Return code: {proc.returncode}")
                        stdout, stderr = await proc.communicate() # Get remaining output
                        if stdout: logging.error(f"Stdout: {stdout.decode(errors='ignore')}")
                        if stderr: logging.error(f"Stderr: {stderr.decode(errors='ignore')}")
                        raise Exception(f"{protocol} server failed to start or exited before ready signal.")

                    line = line_bytes.decode().strip()
                    output_lines.append(line)
                    logging.info(f"{protocol} server output: {line}")
                    if "READY" in line:
                        logging.info(f"{protocol} server is ready.")
                        ready = True
                        break
                except EOFError: # Should be caught by `if not line_bytes` but handle defensively
                    logging.error(f"{protocol} server stream ended unexpectedly.")
                    raise Exception(f"{protocol} server failed to start or stream ended.")

    except asyncio.TimeoutError:
        logging.error(f"{protocol} server did not become ready within {timeout} seconds.")
        logging.error(f"Captured output so far:\n" + "\n".join(output_lines))
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            logging.warning(f"Killing unresponsive {protocol} server after timeout.")
            proc.kill()
        raise Exception(f"{protocol} server timed out.")
    except Exception as e:
        logging.error(f"Error waiting for {protocol} server: {e}")
        # Ensure process is terminated if it's still running
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                 proc.kill()
        raise # Re-raise the exception

    return proc


import pytest_asyncio

@pytest_asyncio.fixture
async def rpc_implementation(request):
    rpc_type = request.config.getoption("--rpc")
    # Pure Python implementation cannot run isolated
    isolated = request.config.getoption("--rpc-isolated") and rpc_type != "pure-python"

    proc = None  # Initialize proc to None
    logging.info(f"Setting up {rpc_type} implementation (isolated={isolated})")

    if rpc_type == "pure-python":
        from implementations.pure_python_impl import PurePythonImplementation
        impl = PurePythonImplementation()
        # No setup/teardown needed, but call them for consistency with the interface
        await impl.setup()
        yield impl
        await impl.teardown()
    elif isolated:
        # Dynamic port assignment
        port = get_dynamic_port() # Moved inside elif isolated
        if rpc_type == "rpyc":
            cmd = [sys.executable, "-u", "launch_rpyc.py", "--port", str(port)]
            proc = await launch_and_wait(cmd, "RPyC")
            from implementations.rpyc_impl import RPyCImplementation
            impl = RPyCImplementation(host="localhost", port=port, external_server=True)
            def connect():
                import rpyc
                impl.conn = rpyc.connect(impl.host, impl.port)
            await asyncio.get_running_loop().run_in_executor(None, connect)
            yield impl
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
        elif rpc_type == "named-pipe":
            if os.name != "nt":
                pytest.skip("Named pipes are only supported on Windows")
            import uuid
            pipe_name = r"\\.\pipe\RPyC_{}".format(uuid.uuid4().hex)
            cmd = [sys.executable, "-u", "launch_named_pipe.py", "--pipe-name", pipe_name]
            proc = await launch_and_wait(cmd, "Named Pipe")
            from named_pipe_impl import NamedPipeImplementation
            impl = NamedPipeImplementation(external_server=True)
            impl.pipe_name = pipe_name
            await impl.setup()
            yield impl
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
        elif rpc_type == "pyro":
            # Assumes Pyro Name Server is running and accessible
            object_name = f"example.benchmark.{uuid.uuid4().hex}"
            cmd = [sys.executable, "-u", "launch_pyro.py", "--name", object_name]
            proc = await launch_and_wait(cmd, "Pyro")
            from implementations.pyro_impl import PyroImplementation
            impl = PyroImplementation(external_server=True, object_name=object_name)
            await impl.setup()  # Connects proxy via NS
            yield impl
            # Terminate the process - our improved launcher will clean up the name server registration
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logging.warning("Pyro server did not terminate gracefully, killing it")
                proc.kill()
        elif rpc_type == "pyro5":
            # Assumes Pyro5 Name Server is running and accessible
            object_name = f"example.benchmark.pyro5.{uuid.uuid4().hex}"
            cmd = [sys.executable, "-u", "launch_pyro5.py", "--name", object_name]
            proc = await launch_and_wait(cmd, "Pyro5")
            from implementations.pyro5_impl import Pyro5Implementation
            impl = Pyro5Implementation(external_server=True, object_name=object_name)
            await impl.setup()  # Connects proxy via NS
            yield impl
            # Terminate the process - our improved launcher will clean up the name server registration
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logging.warning("Pyro5 server did not terminate gracefully, killing it")
                proc.kill()
        elif rpc_type == "grpc":
            cmd = [sys.executable, "-u", "launch_grpc.py", "--port", str(port)]
            proc = await launch_and_wait(cmd, "gRPC")
            from implementations.grpc_impl import GRPCImplementation
            impl = GRPCImplementation(port=port, external_server=True)
            await impl.setup()
            yield impl
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
        elif rpc_type == "zmq":
            cmd = [sys.executable, "-u", "launch_zmq.py", "--port", str(port)]
            proc = await launch_and_wait(cmd, "ZeroMQ")
            from implementations.zmq_impl import ZMQImplementation
            impl = ZMQImplementation(external_server=True)
            impl.simple_endpoint = f"tcp://127.0.0.1:{port}"
            await asyncio.sleep(0.1)
            yield impl
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
    elif not isolated: # Handle non-isolated cases (excluding pure-python handled above)
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
        elif rpc_type == "pyro":
            from implementations.pyro_impl import PyroImplementation
            impl = PyroImplementation()  # Starts internal Pyro4 daemon
        elif rpc_type == "pyro5":
            from implementations.pyro5_impl import Pyro5Implementation
            impl = Pyro5Implementation() # Starts internal Pyro5 daemon
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
