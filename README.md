# NVDA RPC Benchmarking Suite

This project is a benchmarking suite for evaluating different RPC mechanisms for NVDA's remote add-on runtime. It currently supports four RPC implementations:

- RPyC - A transparent Python RPC framework
- ZeroMQ (ZMQ) - A distributed messaging library
- gRPC - Google's high performance RPC framework
- Named Pipes (Windows only) - Using RPyC over Windows named pipes

The suite uses pytest-benchmark to provide detailed performance metrics. For detailed information about the benchmarking approach and test cases, see the [benchmark plan](plan.md).

## Setup

1. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the benchmarks using the provided scripts:

   ```bash
   # On Windows, use the batch file
   run_benchmarks.bat

   # Or use PowerShell
   .\run_benchmarks.ps1
   ```

## Running Specific Implementations

You can run benchmarks for specific RPC implementations:

```bash
# Using batch file
run_benchmarks.bat --implementations rpyc zmq

# Using PowerShell
.\run_benchmarks.ps1 -Implementations rpyc,zmq
```

To run the RPC server in an isolated process:

```bash
# Using batch file
run_benchmarks.bat --isolated

# Using PowerShell
.\run_benchmarks.ps1 -Isolated
```

To run a specific test:

```bash
# Using batch file
run_benchmarks.bat --test test_benchmark_simple_call

# Using PowerShell
.\run_benchmarks.ps1 -Test test_benchmark_simple_call
```

## Viewing Results

After running the benchmarks, you can view the results:

```bash
# View summary
python view_results.py --results-dir benchmark_results/latest

# View details for a specific implementation
python view_results.py --results-dir benchmark_results/latest --implementation rpyc

# View details for a specific test
python view_results.py --results-dir benchmark_results/latest --test test_benchmark_simple_call
```

## Advanced Usage

You can still run the benchmarks directly using pytest:

```bash
pytest --benchmark-enable --rpc=rpyc
pytest --benchmark-enable --rpc=zmq
pytest --benchmark-enable --rpc=grpc
pytest --benchmark-enable --rpc=named-pipe  # Windows only
pytest --benchmark-enable --rpc=named-pipe --rpc-isolated
```
