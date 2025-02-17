def __getattr__(name):
    if name in {"rpc_pb2", "rpc_pb2_grpc"}:
        import importlib
        return importlib.import_module(f"proto.{name}")
    raise AttributeError(f"module {__name__} has no attribute {name}")
