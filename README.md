# NVDA RPC Benchmarking Suite

This project is a benchmarking suite for evaluating different RPC mechanisms for NVDA's remote add-on runtime. Currently, it includes a benchmarking suite for RPyC using pytest-benchmark.

## Setup

1. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the benchmarks using pytest:

   ```bash
   pytest --benchmark-enable
   ```

## Files

- `tests/test_rpyc_benchmark.py`: Contains the benchmarking test for RPyC.
- `requirements.txt`: Lists all necessary Python packages.

## Notes

Ensure that no other services are running on the ports used by the benchmarks.
