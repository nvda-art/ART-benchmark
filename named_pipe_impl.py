import asyncio
import threading
import os
import uuid
from typing import AsyncIterator
import rpyc
from rpyc.utils.server import ThreadedServer
from rpyc.core.stream import NamedPipeStream
from interface import RPCImplementation

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
        if not hasattr(conn_stream, "_fileno"):
            conn_stream._fileno = 0
        if not hasattr(conn_stream, "send"):
            conn_stream.send = conn_stream.write
        self._authenticate_and_serve_client(conn_stream)

    def _serve_client(self, sock, credentials):
        if not hasattr(sock, "getpeername"):
            sock.getpeername = lambda: (self.pipe_name, 0)
        if not hasattr(sock, "getsockname"):
            sock.getsockname = lambda: (self.pipe_name, 0)
        addrinfo = sock.getpeername()
        self.logger.info(f"welcome {addrinfo}")
        try:
            config = dict(self.protocol_config,
                          credentials=credentials,
                          endpoints=(sock.getsockname(), addrinfo),
                          logger=self.logger)
            from rpyc.core.channel import Channel
            conn = self.service._connect(Channel(sock), config)
            self._handle_connection(conn)
        finally:
            self.logger.info(f"goodbye {addrinfo}")

class BenchmarkService(rpyc.Service):
    def exposed_simple_call(self, value):
        # For demonstration, simply multiply value by 2
        return value * 2

    def exposed_stream_values(self, count):
        # Return a generator yielding values from 0 to count-1
        for i in range(count):
            yield i

class NamedPipeImplementation(RPCImplementation):
    def __init__(self, external_server=False):
        if os.name != "nt":
            raise RuntimeError("Named pipes are only supported on Windows")
        
        self.pipe_name = r"\\.\pipe\RPyC_{}".format(uuid.uuid4().hex)
        self.external_server = external_server
        
        if not external_server:
            self.server = NamedPipeServer(
                BenchmarkService,
                port=0,
                protocol_config={"allow_public_attrs": True}
            )
            self.server.pipe_name = self.pipe_name
        else:
            self.server = None
            
        self.server_thread = None
        self.conn = None

    async def setup(self):
        loop = asyncio.get_running_loop()
        if self.server is not None:
            def start_server():
                self.server.start()
            self.server_thread = threading.Thread(target=start_server, daemon=True)
            self.server_thread.start()
            # Wait briefly to ensure the server starts
            await asyncio.sleep(0.5)
            
        def connect():
            from rpyc.core.stream import NamedPipeStream
            from rpyc.utils.factory import connect_stream
            stream = NamedPipeStream.create_client(self.pipe_name)
            self.conn = connect_stream(stream, service=BenchmarkService)
            
        # Try to connect with retries
        max_retries = 5
        for i in range(max_retries):
            try:
                await loop.run_in_executor(None, connect)
                break
            except Exception as e:
                if i == max_retries - 1:
                    raise
                await asyncio.sleep(0.5)

    async def teardown(self):
        if self.conn:
            self.conn.close()
        if self.server:
            self.server.close()
            self.server = None
        if self.server_thread:
            self.server_thread.join(timeout=1)
            self.server_thread = None

    async def simple_call(self, value) -> object:
        loop = asyncio.get_running_loop()
        def remote_call():
            try:
                return self.conn.root.simple_call(value)
            except Exception as e:
                import logging
                logging.error(f"Named pipe simple_call error: {e}")
                return None
        try:
            result = await asyncio.wait_for(loop.run_in_executor(None, remote_call), timeout=15.0)
            return result
        except asyncio.TimeoutError:
            import logging
            logging.error("Named pipe simple_call timeout")
            return None
        except Exception as e:
            import logging
            logging.error(f"Named pipe simple_call unexpected error: {e}")
            return None

    async def stream_values(self, count: int) -> AsyncIterator[int]:
        loop = asyncio.get_running_loop()
        def remote_stream():
            return list(self.conn.root.stream_values(count))
        result = await loop.run_in_executor(None, remote_stream)
        for item in result:
            yield item
