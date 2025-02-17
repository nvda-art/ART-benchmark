# NVDA RPC Benchmarking Suite

This project is a benchmarking suite for evaluating different RPC mechanisms for NVDA's remote add-on runtime. Currently, it includes a benchmarking suite for RPyC using pytest-benchmark. For detailed information about the benchmarking approach and test cases, see the [benchmark plan](plan.md).

## Setup

1. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the benchmarks using pytest:

   ```bash
   pytest --benchmark-enable
   ```
