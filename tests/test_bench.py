import asyncio
import logging
import pytest



def test_benchmark_simple_call(rpc_implementation, benchmark):
    """Benchmark concurrent simple RPC calls"""
    num_calls = 50  # Define the number of operations

    def run_test():
        async def concurrent_test():
            # Run num_calls concurrent RPC calls with a limit of 10 at a time
            semaphore = asyncio.Semaphore(10)

            async def single_call():
                async with semaphore:
                    return await rpc_implementation.simple_call(42)

            tasks = [single_call() for _ in range(num_calls)] # Use num_calls
            return await asyncio.gather(*tasks)

        results = asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(concurrent_test(), timeout=120)
        )

        return results

    # Add extra info BEFORE running the benchmark
    benchmark.extra_info['operations'] = num_calls
    results = benchmark(run_test)

    # Check for exceptions in results
    for result in results:
        if isinstance(result, Exception):
            pytest.fail(f"RPC call failed with: {result}")

    # Verify correct return values
    for result in results:
        assert result == 84


def test_benchmark_stream_thousand(rpc_implementation, benchmark):
    """Benchmark streaming 1000 values from RPC"""
    num_values = 1000 # Define the number of operations

    async def _run_stream_test():
        # No try/except - let exceptions propagate
        result = []
        try:
            # Iterate directly over the async iterator
            async for x in rpc_implementation.stream_values(num_values): # Use num_values
                result.append(x)
                if len(result) % 100 == 0:
                    await asyncio.sleep(0)  # Yield control periodically
        except Exception as e:
            logging.error(f"Stream test error during collection: {e}")
            pytest.fail(f"Stream collection failed: {e}")
        finally:
            logging.info(f"Stream test collected {len(result)} items before finishing/failing.")
        return result

    def run_benchmark_wrapper():
        # Run the async test function to completion using the event loop
        return asyncio.get_event_loop().run_until_complete(_run_stream_test())

    # Add extra info
    benchmark.extra_info['operations'] = num_values
    # Run the benchmark for timing, but we can't use its return value directly
    benchmark(run_benchmark_wrapper)

    # Run the async function again explicitly to get the actual result list for assertion
    # Note: We run the test again for assertion; benchmark runs it internally for timing.
    results_list = asyncio.get_event_loop().run_until_complete(_run_stream_test())
    # Assert on the result of the explicit run
    assert len(results_list) == num_values

