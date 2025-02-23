#!/usr/bin/env python
import sys
import os
from grpc_tools import protoc

def main():
    proto_dir = os.path.join(os.path.dirname(__file__), "proto")
    proto_file = os.path.join(proto_dir, "rpc.proto")
    if not os.path.exists(proto_file):
        print("rpc.proto not found in proto directory.")
        sys.exit(1)
    ret = protoc.main([
        "",
        f"-I{proto_dir}",
        f"--python_out={proto_dir}",
        f"--grpc_python_out={proto_dir}",
        proto_file,
    ])
    if ret != 0:
        print("Error: Protoc returned non-zero exit status")
        sys.exit(ret)
    print("Successfully built gRPC stubs.")

if __name__ == "__main__":
    main()
