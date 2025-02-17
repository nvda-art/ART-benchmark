# RPC Framework Benchmark Plan

## Purpose
We're building a benchmarking suite to compare the real-world performance characteristics of different Python RPC frameworks (RPyC, ZeroMQ, and gRPC) in a Windows environment. This will help developers make informed decisions about which framework best suits their needs based on actual performance data rather than assumptions or outdated information.

## Key Questions We're Answering
1. How do these frameworks compare for basic request/response latency?
2. Which framework handles streaming data most efficiently?
3. How do they perform under concurrent load?
4. What are the memory and CPU costs of each?
5. How do they handle different payload sizes?

## Testing Approach
We'll use pytest-benchmark as our core benchmarking tool because:
- It handles the complexities of accurate timing
- Provides statistical analysis out of the box
- Has good support for async operations
- Can generate comparison reports

## Project Structure
```
rpc-benchmarks/
  ├── proto/              # gRPC definitions
  ├── implementations/    # One file per RPC implementation
  │   ├── rpyc_impl.py
  │   ├── zmq_impl.py
  │   └── grpc_impl.py
  ├── tests/             # Benchmark tests
  │   └── test_bench.py
  ├── conftest.py        # pytest fixtures
  └── requirements.txt
```

## Common Interface
Each implementation must satisfy this base interface:

```python
class RPCImplementation:
    async def setup()
    async def teardown()
    async def simple_call(value: int) -> int
    async def stream_values(count: int) -> AsyncIterator[int]
```

## Test Cases
Our test cases model real-world usage patterns:

### 1. Simple Calls - Measuring Baseline Latency
- Small integer/string payloads
- Simulates typical API calls
- Focus on latency and request rate

Example implementation:
```python
def test_simple_call(benchmark, rpc_implementation):
    benchmark(rpc_implementation.simple_call, 42)
```

### 2. Streaming Performance
- Stream sequences of integers
- Tests both throughput and latency
- Reveals buffering behavior
- Important for real-time data feeds

Example implementation:
```python
def test_stream_thousand(benchmark, rpc_implementation):
    benchmark(lambda: list(rpc_implementation.stream_values(1000)))
```

### 3. Large Payload Handling
- Various payload sizes (1KB to 10MB)
- Shows serialization costs
- Network efficiency differences
- Critical for bulk data transfer

Each case will run in isolation and under concurrent load to reveal real-world behavior.

## Implementation-Specific Details
- RPyC: Use their async features for streaming
- ZeroMQ: Use pyzmq async API with REQ/REP for simple calls, PUSH/PULL for streaming
- gRPC: Use standard streaming features

## Windows-Specific Strategy
Windows presents unique challenges:
- Process management differs from Unix
- Network stack has different behavior
- File locking affects IPC
- PowerShell is our primary automation tool

We'll manage this by:
1. Using PowerShell for test orchestration (with batch fallbacks)
2. Handling Windows paths and file operations explicitly
3. Proper process cleanup in teardown
4. Managing Windows-specific network behavior

## Running Strategy
- Each implementation runs in separate process for isolation
- Use pytest fixtures for setup/teardown
- Execute benchmarks with:
  ```bash
  pytest --benchmark-only --benchmark-compare
  ```

## Development Phases
1. Define the common interface - exactly what operations we're benchmarking
2. Create the pytest fixtures for measurements
3. Build one implementation (probably RPyC) to validate the harness
4. Add remaining implementations
5. Develop analysis and reporting scripts
