import asyncio
import threading
from typing import AsyncIterator
import rpyc
from rpyc.utils.server import ThreadedServer
from interface import RPCImplementation

class BenchmarkService(rpyc.Service):
    def exposed_simple_call(self, value):
        # For demonstration, simply multiply value by 2
        return value * 2

    def exposed_stream_values(self, count):
        # Return a generator yielding values from 0 to count-1
        for i in range(count):
            yield i

class RPyCImplementation(RPCImplementation):
    def __init__(self, host='localhost', port=18861, external_server=False):
        self.host = host
        self.port = port
        if not external_server:
            self.server = ThreadedServer(
                BenchmarkService,
                port=port,
                protocol_config={"allow_public_attrs": True}
            )
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
            self.conn = rpyc.connect(self.host, self.port)
        await loop.run_in_executor(None, connect)

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
            return self.conn.root.simple_call(value)
        result = await loop.run_in_executor(None, remote_call)
        return result

    async def stream_values(self, count: int) -> AsyncIterator[int]:
        loop = asyncio.get_running_loop()
        def remote_stream():
            return list(self.conn.root.stream_values(count))
        result = await loop.run_in_executor(None, remote_stream)
        for item in result:
            yield item
