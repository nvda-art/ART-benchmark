import asyncio

import pytest


def test_benchmark_large_payload(rpc_implementation, benchmark):
    """Benchmark RPC calls with payloads of increasing sizes"""

    def run_test():
        async def concurrent_payload_test():
            # Define payload sizes to test
            sizes = [1024, 10*1024, 100*1024, 1024*1024]

            # Run concurrent calls with different payload sizes
            tasks = [rpc_implementation.simple_call(
                "x" * size) for size in sizes]
            results = await asyncio.gather(*tasks)

            return list(zip(sizes, results))

        return asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(concurrent_payload_test(), timeout=180)
        )

    results = benchmark(run_test)

    # Check for exceptions in results
    for size, result in results:
        if isinstance(result, Exception):
            pytest.fail(f"RPC call with size {size} failed with: {result}")

    # Verify correct return values
    for size, result in results:
        assert len(result) == 2 * \
            size, f"Expected result length {2*size}, got {len(result)}"
