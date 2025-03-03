# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

from proto import rpc_pb2 as rpc__pb2

GRPC_GENERATED_VERSION = '1.70.0'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in rpc_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class RPCServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.SimpleCall = channel.unary_unary(
                '/rpc.RPCService/SimpleCall',
                request_serializer=rpc__pb2.SimpleRequest.SerializeToString,
                response_deserializer=rpc__pb2.SimpleResponse.FromString,
                _registered_method=True)
        self.StreamValues = channel.unary_stream(
                '/rpc.RPCService/StreamValues',
                request_serializer=rpc__pb2.StreamRequest.SerializeToString,
                response_deserializer=rpc__pb2.StreamResponse.FromString,
                _registered_method=True)


class RPCServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def SimpleCall(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def StreamValues(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_RPCServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'SimpleCall': grpc.unary_unary_rpc_method_handler(
                    servicer.SimpleCall,
                    request_deserializer=rpc__pb2.SimpleRequest.FromString,
                    response_serializer=rpc__pb2.SimpleResponse.SerializeToString,
            ),
            'StreamValues': grpc.unary_stream_rpc_method_handler(
                    servicer.StreamValues,
                    request_deserializer=rpc__pb2.StreamRequest.FromString,
                    response_serializer=rpc__pb2.StreamResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'rpc.RPCService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('rpc.RPCService', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class RPCService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def SimpleCall(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/rpc.RPCService/SimpleCall',
            rpc__pb2.SimpleRequest.SerializeToString,
            rpc__pb2.SimpleResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def StreamValues(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_stream(
            request,
            target,
            '/rpc.RPCService/StreamValues',
            rpc__pb2.StreamRequest.SerializeToString,
            rpc__pb2.StreamResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
