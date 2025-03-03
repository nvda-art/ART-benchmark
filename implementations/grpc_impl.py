import asyncio
try:
    import grpc
    import grpc.aio
except ImportError as e:
    raise ImportError("grpc and grpc.aio are required for GRPCImplementation. Please install them via 'pip install grpcio grpcio-tools'.") from e
try:
    from proto import rpc_pb2, rpc_pb2_grpc
except ImportError as e:
    import logging
    logging.error("gRPC stubs not found. Please run build_protos.py to generate them.")
    raise e
from interface import RPCImplementation

class GRPCServiceServicer(rpc_pb2_grpc.RPCServiceServicer):
    async def SimpleCall(self, request, context):
        import logging
        if request.WhichOneof("payload") == "int_value":
            logging.info("GRPC SimpleCall received int request: %d", request.int_value)
            result = request.int_value * 2
            response = rpc_pb2.SimpleResponse(int_value=result)
        else:
            logging.info("GRPC SimpleCall received string request of length: %d", len(request.str_value))
            result = request.str_value * 2
            response = rpc_pb2.SimpleResponse(str_value=result)
        
        if response.WhichOneof("payload") == "int_value":
            logging.info("GRPC SimpleCall sending int response: %d", response.int_value)
        else:
            logging.info("GRPC SimpleCall sending string response of length: %d", len(response.str_value))
        return response

    async def StreamValues(self, request, context):
        import logging
        logging.info("GRPC StreamValues received request with count: %d", request.count)
        for i in range(request.count):
            yield rpc_pb2.StreamResponse(value=i)
        logging.info("GRPC StreamValues finished sending responses")

class GRPCImplementation(RPCImplementation):
    def __init__(self, port=50051, external_server=False):
        self.port = port
        self.external_server = external_server
        import logging
        logging.info("GRPCImplementation.__init__ called with port %d, external_server=%s", port, external_server)
        self.server = None
        self.channel = None
        self.stub = None

    async def setup(self):
        import logging
        logging.info("Entering GRPCImplementation.setup(), external_server=%s", self.external_server)
        if not self.external_server:
            self.server = grpc.aio.server()
            rpc_pb2_grpc.add_RPCServiceServicer_to_server(GRPCServiceServicer(), self.server)
            self.server.add_insecure_port(f"127.0.0.1:{self.port}")
            await self.server.start()
            logging.info(f"gRPC server started on port {self.port}")
        await asyncio.sleep(0.5)
        logging.debug("GRPCImplementation.setup: current event loop id: %s", id(asyncio.get_running_loop()))
        options = [
            ('grpc.max_send_message_length', 50 * 1024 * 1024),
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),
        ]
        self.channel = grpc.aio.insecure_channel(f"127.0.0.1:{self.port}", options=options)
        self.stub = rpc_pb2_grpc.RPCServiceStub(self.channel)
        logging.info("Attempting to connect to gRPC server at 127.0.0.1:%d", self.port)
        try:
            logging.info("Channel connectivity state before waiting: %s", self.channel.get_state())
            logging.info("Waiting for gRPC channel to be ready with timeout=5")
            await asyncio.wait_for(self.channel.channel_ready(), timeout=5)
            logging.info("gRPC channel is ready, current state: %s", self.channel.get_state())
        except Exception as e:
            logging.error("Error waiting for gRPC channel readiness: %s", e)
            raise

    async def teardown(self):
        if self.channel:
            await self.channel.close()
        if self.server and not self.external_server:
            await self.server.stop(0)
            try:
                await asyncio.wait_for(self.server.wait_for_termination(), timeout=5)
            except asyncio.TimeoutError:
                pass

    async def simple_call(self, value) -> object:
        import logging, asyncio, grpc
        logging.debug("GRPC simple_call using event loop id: %s", id(asyncio.get_running_loop()))
        try:
            if isinstance(value, int):
                request = rpc_pb2.SimpleRequest(int_value=value)
                logging.info("GRPC simple_call sending int request: %d", value)
            else:
                request = rpc_pb2.SimpleRequest(str_value=value)
                logging.info("GRPC simple_call sending string request of length: %d", len(value))
            
            # Use timeout for the entire call
            try:
                call = self.stub.SimpleCall(request, wait_for_ready=True)
                logging.debug("GRPC simple_call: awaiting call result")
                response = await asyncio.wait_for(call, timeout=15.0)
                
                if response.WhichOneof("payload") == "int_value":
                    logging.info("GRPC simple_call received int response: %d", response.int_value)
                    return response.int_value
                else:
                    logging.info("GRPC simple_call received string response of length: %d", len(response.str_value))
                    return response.str_value
            except asyncio.TimeoutError:
                logging.error("GRPC simple_call: timeout waiting for response")
                return None
            except grpc.aio.AioRpcError as e:
                logging.error(f"GRPC simple_call: RPC error: {e.code()}: {e.details()}")
                return None
        except Exception as e:
            logging.error(f"GRPC simple_call: unexpected error: {e}")
            return None

    async def stream_values(self, count: int):
        import logging
        request = rpc_pb2.StreamRequest(count=count)
        logging.info("GRPC stream_values sending request: %s", request)
        async for response in self.stub.StreamValues(request, wait_for_ready=True):
            logging.info("GRPC stream_values received response: %s", response)
            yield response.value
