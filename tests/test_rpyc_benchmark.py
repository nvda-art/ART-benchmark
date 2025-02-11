import pytest
import threading
import time
import os
import uuid
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

@pytest.fixture(scope="module")
def named_pipe_server():
    if os.name != "nt":
        pytest.skip("Named pipes benchmark only supported on Windows")
    pipe_name = r"\\.\pipe\RPyC_{}".format(uuid.uuid4().hex)

    class NamedPipeListener:
        def __init__(self, pipe_name):
            self.pipe_name = pipe_name
        def accept(self):
            from rpyc.core.stream import NamedPipeStream
            stream = NamedPipeStream.create_server(self.pipe_name, connect=True)
            return stream, None
        def close(self):
            pass

    listener = NamedPipeListener(pipe_name)
    server = ThreadedServer(TestService, sock=listener, protocol_config={"allow_public_attrs": True})
    thread = threading.Thread(target=server.start)
    thread.daemon = True
    thread.start()
    time.sleep(0.1)
    server.pipe_name = pipe_name
    yield server
    server.close()
    thread.join()

@pytest.fixture
def named_pipe_client(named_pipe_server):
    if os.name != "nt":
        pytest.skip("Named pipes benchmark only supported on Windows")
    conn = rpyc.connect_pipe(named_pipe_server.pipe_name, service=TestService)
    yield conn
    conn.close()

def test_named_pipe_echo(benchmark, named_pipe_client):
    def remote_echo():
        return named_pipe_client.root.echo("pipe test")
    result = benchmark(remote_echo)
    assert result == "pipe test"
