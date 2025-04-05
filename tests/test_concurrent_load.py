import asyncio
import logging
import pytest


@pytest.mark.parametrize("concurrency", [1, 5, 10, 20, 50, 100])
def test_benchmark_simple_call(rpc_implementation, benchmark, concurrency):
    """Benchmark simple RPC calls with varying concurrency levels"""

    total_calls = 200 # Define the number of operations

    def run_test():
        async def concurrent_test():
            semaphore = asyncio.Semaphore(concurrency)

            async def limited_call():
                async with semaphore:
                    return await rpc_implementation.simple_call(42)

            tasks = [limited_call() for _ in range(total_calls)]
            return await asyncio.gather(*tasks)

        return asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(concurrent_test(), timeout=60)
        )

    # Add extra info BEFORE running the benchmark
    benchmark.extra_info['operations'] = total_calls
    # Run the benchmark
    results = benchmark(run_test)

    # Log concurrency information
    logging.info(
        f"Completed benchmark with concurrency={concurrency}, calls={total_calls}")

    # Check for exceptions in results
    for result in results:
        if isinstance(result, Exception):
            pytest.fail(f"RPC call failed with: {result}")

    # Verify correct return values
    for result in results:
        assert result == 84
