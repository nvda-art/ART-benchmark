from typing import Optional

# Minimal stub for gRPC generated file (rpc_pb2.py) from rpc.proto

class SimpleRequest:
    def __init__(self, int_value: Optional[int] = None, str_value: Optional[str] = None):
        self.int_value = int_value
        self.str_value = str_value

    def WhichOneof(self, oneof_name):
        if oneof_name == "payload":
            if self.int_value is not None:
                return "int_value"
            elif self.str_value is not None:
                return "str_value"
        return None

class SimpleResponse:
    def __init__(self, int_value: Optional[int] = None, str_value: Optional[str] = None):
        self.int_value = int_value
        self.str_value = str_value

    def WhichOneof(self, oneof_name):
        if oneof_name == "payload":
            if self.int_value is not None:
                return "int_value"
            elif self.str_value is not None:
                return "str_value"
        return None

class StreamRequest:
    def __init__(self, count: int):
        self.count = count

class StreamResponse:
    def __init__(self, value: int):
        self.value = value
