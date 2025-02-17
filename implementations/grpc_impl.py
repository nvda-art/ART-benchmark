import asyncio
try:
    import grpc
    import grpc.aio
except ImportError as e:
    raise ImportError("grpc and grpc.aio are required for GRPCImplementation. Please install them via 'pip install grpcio grpcio-tools'.") from e
from proto import rpc_pb2, rpc_pb2_grpc
from interface import RPCImplementation

class GRPCServiceServicer(rpc_pb2_grpc.RPCServiceServicer):
    async def SimpleCall(self, request, context):
        if request.WhichOneof("payload") == "int_value":
            result = request.int_value * 2
            return rpc_pb2.SimpleResponse(int_value=result)
        else:
            result = request.str_value * 2
            return rpc_pb2.SimpleResponse(str_value=result)

    async def StreamValues(self, request, context):
        for i in range(request.count):
            yield rpc_pb2.StreamResponse(value=i)

class GRPCImplementation(RPCImplementation):
    def __init__(self, port=50051):
        self.port = port
        self.server = None
        self.channel = None
        self.stub = None

    async def setup(self):
        self.server = grpc.aio.server()
        rpc_pb2_grpc.add_RPCServiceServicer_to_server(GRPCServiceServicer(), self.server)
        self.server.add_insecure_port(f"[::]:{self.port}")
        await self.server.start()
        await asyncio.sleep(0.5)
        self.channel = grpc.aio.insecure_channel(f"localhost:{self.port}")
        self.stub = rpc_pb2_grpc.RPCServiceStub(self.channel)

    async def teardown(self):
        if self.channel:
            await self.channel.close()
        if self.server:
            await self.server.stop(0)
            try:
                await asyncio.wait_for(self.server.wait_for_termination(), timeout=5)
            except asyncio.TimeoutError:
                pass

    async def simple_call(self, value) -> object:
        if isinstance(value, int):
            request = rpc_pb2.SimpleRequest(int_value=value)
        else:
            request = rpc_pb2.SimpleRequest(str_value=value)
        response = await self.stub.SimpleCall(request)
        if response.WhichOneof("payload") == "int_value":
            return response.int_value
        else:
            return response.str_value

    async def stream_values(self, count: int):
        request = rpc_pb2.StreamRequest(count=count)
        async for response in self.stub.StreamValues(request):
            yield response.value
