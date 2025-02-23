import asyncio
try:
    import zmq
    import zmq.asyncio
except ImportError as e:
    raise ImportError("pyzmq is required to use ZMQImplementation. Please install it via 'pip install pyzmq'.") from e
from interface import RPCImplementation
from zmq.utils.monitor import parse_monitor_message

class ZMQImplementation(RPCImplementation):
    def __init__(self, external_server=False):
        self.ctx = zmq.asyncio.Context.instance()
        self.external_server = external_server
        self.simple_endpoint = "tcp://127.0.0.1:5555"
        self.stream_req_endpoint = "tcp://127.0.0.1:5557"
        self.stream_pull_endpoint = "tcp://127.0.0.1:5556"
        self.simple_server_task = None
        self.stream_server_task = None
        self.simple_client = None

    async def setup(self):
        if not self.external_server:
            self.simple_server_task = asyncio.create_task(self.run_simple_server())
            self.stream_server_task = asyncio.create_task(self.run_stream_server())
        self.simple_client = self.ctx.socket(zmq.REQ)
        self.simple_client.connect(self.simple_endpoint)
        await asyncio.sleep(0.5)

    async def teardown(self):
        if not self.external_server:
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
        await asyncio.sleep(0.5)
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
        import logging
        logging.info("ZMQ simple_call: Connecting to %s", self.simple_endpoint)
        socket = self.ctx.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        # Set up socket monitoring to wait for connection.
        monitor_endpoint = f"inproc://monitor.req.{id(socket)}"
        socket.monitor(monitor_endpoint, zmq.EVENT_CONNECTED)
        monitor = self.ctx.socket(zmq.PAIR)
        monitor.connect(monitor_endpoint)
        socket.connect(self.simple_endpoint)
        # Wait until the socket is connected.
        while True:
            msg = await monitor.recv_multipart()
            event = parse_monitor_message(msg)
            if event["event"] == zmq.EVENT_CONNECTED:
                logging.info("ZMQ simple_call: Socket connected.")
                break
        await asyncio.sleep(0.2)
        socket.disable_monitor()
        monitor.close()
        #logging.info("ZMQ simple_call: Sending value %s", value)
        await socket.send_json({"value": value})
        logging.info("ZMQ simple_call: Waiting for reply...")
        response = await socket.recv_json()
        # logging.info("ZMQ simple_call: Received response %s", response)
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
