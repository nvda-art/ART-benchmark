# NVDA RPC Benchmarking Suite

This project is a benchmarking suite for evaluating different RPC mechanisms for NVDA's remote add-on runtime. It currently supports three RPC implementations:

- RPyC - A transparent Python RPC framework
- ZeroMQ (ZMQ) - A distributed messaging library
- gRPC - Google's high performance RPC framework

The suite uses pytest-benchmark to provide detailed performance metrics. For detailed information about the benchmarking approach and test cases, see the [benchmark plan](plan.md).

## Setup

1. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the benchmarks using pytest:

   ```bash
   pytest --benchmark-enable
   ```
