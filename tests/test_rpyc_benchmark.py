import pytest
import threading
import time
import rpyc
from rpyc.utils.server import ThreadedServer

class TestService(rpyc.Service):
    def exposed_echo(self, msg):
        """Return the message back."""
        return msg

@pytest.fixture(scope="module")
def rpyc_server():
    # Start RPyC server on a random free port (port=0)
    server = ThreadedServer(TestService, port=0, protocol_config={"allow_public_attrs": True})
    thread = threading.Thread(target=server.start)
    thread.daemon = True
    thread.start()
    # Wait briefly for the server to start and determine the actual port
    time.sleep(0.1)
    actual_port = server.listener.getsockname()[1]
    server.port = actual_port
    yield server
    server.close()
    thread.join()

@pytest.fixture
def client(rpyc_server):
    conn = rpyc.connect("localhost", port=rpyc_server.port, service=TestService)
    yield conn
    conn.close()

def test_remote_echo(benchmark, client):
    def remote_echo():
        return client.root.echo("test")
    result = benchmark(remote_echo)
    assert result == "test"
