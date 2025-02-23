import asyncio
import logging
import socket
import subprocess
import sys
import time

import pytest

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s', force=True)


def pytest_addoption(parser):
    parser.addoption("--rpc", action="store", default="rpyc", choices=["rpyc", "zmq", "grpc"],
                     help="Choose the RPC implementation to benchmark.")
    parser.addoption("--rpc-isolated", action="store_true", default=False,
                     help="Run the RPC server in an isolated process.")


def launch_and_wait(cmd, protocol):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    start_time = time.time()
    ready = False
    while time.time() - start_time < 10:
        line = proc.stdout.readline()
        if "READY" in line:
            logging.info(f"{protocol} server is ready.")
            ready = True
            break
    if not ready:
        proc.kill()
        raise Exception(f"{protocol} server did not become ready in time.")
    return proc


@pytest.fixture(scope="module")
def rpc_implementation(request):
    rpc_type = request.config.getoption("--rpc")
    isolated = request.config.getoption("--rpc-isolated")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

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
            loop.run_until_complete(loop.run_in_executor(None, connect))
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
            impl = GRPCImplementation(port=port)
            asyncio.run(asyncio.sleep(0.1))
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
            asyncio.run(asyncio.sleep(0.1))
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
        elif rpc_type == "zmq":
            from implementations.zmq_impl import ZMQImplementation
            impl = ZMQImplementation()
        elif rpc_type == "grpc":
            from implementations.grpc_impl import GRPCImplementation
            impl = GRPCImplementation()
        asyncio.run(impl.setup())
        yield impl
        asyncio.run(impl.teardown())

def get_dynamic_port():
    sock = socket.socket()
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port
