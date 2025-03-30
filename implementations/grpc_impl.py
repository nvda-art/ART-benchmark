import asyncio
import logging
import time

try:
    import grpc
    import grpc.aio
except ImportError as e:
    raise ImportError("grpc and grpc.aio are required for GRPCImplementation. Please install them via 'pip install grpcio grpcio-tools'.") from e

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s [%(levelname)8s] %(filename)s:%(lineno)d %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

# Initialize gRPC async only once
logging.info("Initializing gRPC async")
grpc.aio.init_grpc_aio()
logging.info("gRPC async initialized")
try:
    from proto import rpc_pb2, rpc_pb2_grpc
except ImportError as e:
    import logging
    logging.error("gRPC stubs not found. Please run build_protos.py to generate them.")
    raise e
from interface import RPCImplementation

class GRPCServiceServicer(rpc_pb2_grpc.RPCServiceServicer):
    async def SimpleCall(self, request, context):
        if request.WhichOneof("payload") == "int_value":
            # logging.debug("GRPC SimpleCall received int request: %d", request.int_value)
            result = request.int_value * 2
            response = rpc_pb2.SimpleResponse(int_value=result)
        else:
            # logging.debug("GRPC SimpleCall received string request of length: %d", len(request.str_value))
            result = request.str_value * 2
            response = rpc_pb2.SimpleResponse(str_value=result)
        
        # logging.debug("GRPC SimpleCall sending response")
        return response

    async def StreamValues(self, request, context):
        # logging.debug("GRPC StreamValues received request with count: %d", request.count)
        for i in range(request.count):
            yield rpc_pb2.StreamResponse(value=i)
        # logging.debug("GRPC StreamValues finished sending responses")

class GRPCImplementation(RPCImplementation):
    def __init__(self, port=50051, external_server=False):
        self.port = port
        self.external_server = external_server
        logging.info(f"GRPCImplementation.__init__ called with port {port}, external_server={external_server}")
        self.server = None
        self.channel = None
        self.stub = None
        self._loop = None  # Store the event loop

    async def setup(self):
        # Store the current event loop
        self._loop = asyncio.get_running_loop()
        logging.info(f"Entering GRPCImplementation.setup(), external_server={self.external_server}")
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
        
        # Log before creating channel
        logging.info(f"Creating gRPC channel to 127.0.0.1:{self.port}")
        
        # Create the channel with the current event loop context
        self.channel = grpc.aio.insecure_channel(
            f"127.0.0.1:{self.port}", 
            options=options
        )
        
        # Log after creating channel
        logging.info(f"Channel created: {self.channel}")
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
        try:
            logging.debug(f"Entering simple_call with value type: {type(value)}")
            
            if isinstance(value, int):
                request = rpc_pb2.SimpleRequest(int_value=value)
                logging.info(f"GRPC simple_call sending int request: {value}")
            else:
                request = rpc_pb2.SimpleRequest(str_value=value)
                logging.info(f"GRPC simple_call sending string request of length: {len(value)}")
            
            try:
                # Log before making the RPC call
                logging.info("About to make gRPC SimpleCall")
                
                # Ensure the stub is available
                if not self.stub:
                    logging.error("gRPC stub is not initialized!")
                    raise ConnectionError("gRPC stub not available")
                    
                # Use the stub with explicit timeout
                start_time = time.time()
                response = await self.stub.SimpleCall(request, wait_for_ready=True, timeout=15.0)
                elapsed = time.time() - start_time
                
                # Log after the RPC call
                logging.info(f"gRPC SimpleCall completed in {elapsed:.3f} seconds")
                
                if response.WhichOneof("payload") == "int_value":
                    logging.info("GRPC simple_call received int response: %d", response.int_value)
                    return response.int_value
                else:
                    logging.info("GRPC simple_call received string response of length: %d", len(response.str_value))
                    return response.str_value
            except grpc.aio.AioRpcError as e:
                logging.error(f"GRPC simple_call: RPC error: {e.code()}: {e.details()}")
                return None
        except Exception as e:
            logging.error(f"GRPC simple_call: unexpected error: {e}")
            return None

    async def stream_values(self, count: int):
        request = rpc_pb2.StreamRequest(count=count)
        logging.info(f"GRPC stream_values sending request: {request}")
        
        logging.debug(f"Entering stream_values with count: {count}")
        
        try:
            # Log before making the streaming RPC call
            logging.info("About to make gRPC StreamValues call")

            # Ensure the stub is available
            if not self.stub:
                logging.error("gRPC stub is not initialized!")
                raise ConnectionError("gRPC stub not available")
            
            # Add timeout to the gRPC streaming call
            response_count = 0
            start_time = time.time()
            
            async for response in self.stub.StreamValues(request, wait_for_ready=True, timeout=60.0):
                response_count += 1
                if response_count % 100 == 0:
                    logging.debug(f"GRPC stream_values received {response_count} responses so far")
                
                yield response.value
            
            elapsed = time.time() - start_time
            logging.info(f"gRPC StreamValues completed in {elapsed:.3f} seconds, yielded {response_count} responses")
        except Exception as e:
            logging.error(f"GRPC stream_values error: {e}")
            # Re-raise to let the caller handle it
            raise
