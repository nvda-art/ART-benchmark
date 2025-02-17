import asyncio
try:
    import zmq.asyncio
except ImportError as e:
    raise ImportError("pyzmq is required to use ZMQImplementation. Please install it via 'pip install pyzmq'.") from e
from interface import RPCImplementation

class ZMQImplementation(RPCImplementation):
    def __init__(self):
        self.ctx = zmq.asyncio.Context.instance()
        self.simple_endpoint = "tcp://127.0.0.1:5555"
        self.stream_req_endpoint = "tcp://127.0.0.1:5557"
        self.stream_pull_endpoint = "tcp://127.0.0.1:5556"
        self.simple_server_task = None
        self.stream_server_task = None
        self.simple_client = None

    async def setup(self):
        self.simple_server_task = asyncio.create_task(self.run_simple_server())
        self.stream_server_task = asyncio.create_task(self.run_stream_server())
        self.simple_client = self.ctx.socket(zmq.REQ)
        self.simple_client.connect(self.simple_endpoint)
        await asyncio.sleep(0.5)

    async def teardown(self):
        if self.simple_server_task:
            self.simple_server_task.cancel()
            try:
                await self.simple_server_task
            except asyncio.CancelledError:
                pass
        if self.stream_server_task:
            self.stream_server_task.cancel()
            try:
                await self.stream_server_task
            except asyncio.CancelledError:
                pass
        if self.simple_client:
            self.simple_client.close()
        self.ctx.term()

    async def run_simple_server(self):
        socket = self.ctx.socket(zmq.REP)
        socket.bind(self.simple_endpoint)
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(socket.recv_json(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                value = msg["value"]
                result = value * 2
                await socket.send_json({"result": result})
        except asyncio.CancelledError:
            pass
        finally:
            socket.close()

    async def run_stream_server(self):
        rep_socket = self.ctx.socket(zmq.REP)
        push_socket = self.ctx.socket(zmq.PUSH)
        rep_socket.bind(self.stream_req_endpoint)
        push_socket.bind(self.stream_pull_endpoint)
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(rep_socket.recv_json(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                count = msg["count"]
                await rep_socket.send_json({"ack": True})
                for i in range(count):
                    await push_socket.send_json({"value": i})
        except asyncio.CancelledError:
            pass
        finally:
            rep_socket.close()
            push_socket.close()

    async def simple_call(self, value) -> object:
        # Create a new REQ socket for each call to support concurrent operations
        socket = self.ctx.socket(zmq.REQ)
        socket.connect(self.simple_endpoint)
        await socket.send_json({"value": value})
        response = await socket.recv_json()
        socket.close()
        return response["result"]

    async def stream_values(self, count: int):
        req_socket = self.ctx.socket(zmq.REQ)
        req_socket.connect(self.stream_req_endpoint)
        await req_socket.send_json({"count": count})
        await req_socket.recv_json()  # wait for acknowledgement
        req_socket.close()
        pull_socket = self.ctx.socket(zmq.PULL)
        pull_socket.connect(self.stream_pull_endpoint)
        for _ in range(count):
            msg = await pull_socket.recv_json()
            yield msg["value"]
        pull_socket.close()
