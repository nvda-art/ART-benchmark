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

class NamedPipeServer(ThreadedServer):
    def _listen(self):
        from rpyc.core.stream import NamedPipeStream
        self.active = True
        # Use the proper NamedPipeStream interface to create a server-side stream.
        conn_stream = NamedPipeStream.create_server(self.pipe_name, connect=True)
        if not hasattr(conn_stream, "getpeername"):
            conn_stream.getpeername = lambda: (self.pipe_name, 0)
        if not hasattr(conn_stream, "getsockname"):
            conn_stream.getsockname = lambda: (self.pipe_name, 0)
        self._authenticate_and_serve_client(conn_stream)

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
    server = NamedPipeServer(TestService, port=0, protocol_config={"allow_public_attrs": True})
    server.pipe_name = pipe_name
    thread = threading.Thread(target=server.start)
    thread.daemon = True
    thread.start()
    time.sleep(0.1)
    yield server
    server.close()
    thread.join()

@pytest.fixture
def named_pipe_client(named_pipe_server):
    if os.name != "nt":
        pytest.skip("Named pipes benchmark only supported on Windows")
    from rpyc.core.stream import NamedPipeStream
    from rpyc.utils.factory import connect_stream
    import time
    timeout = time.time() + 5
    stream = None
    while time.time() < timeout:
        try:
            stream = NamedPipeStream.create_client(named_pipe_server.pipe_name)
            break
        except Exception:
            time.sleep(0.1)
    if stream is None:
        pytest.fail("Failed to connect to named pipe")
    conn = connect_stream(stream, service=TestService)
    yield conn
    conn.close()

def test_named_pipe_echo(benchmark, named_pipe_client):
    def remote_echo():
        return named_pipe_client.root.echo("pipe test")
    result = benchmark(remote_echo)
    assert result == "pipe test"
