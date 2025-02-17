import asyncio
import pytest
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', force=True)

def pytest_addoption(parser):
    parser.addoption("--rpc", action="store", default="rpyc", choices=["rpyc", "zmq", "grpc"], help="Choose the RPC implementation to benchmark.")

@pytest.fixture(scope="module")
def rpc_implementation(request):
    rpc_type = request.config.getoption("--rpc")
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
