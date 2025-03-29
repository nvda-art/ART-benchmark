import asyncio
import logging
import pytest



def test_benchmark_simple_call(rpc_implementation, benchmark):
    """Benchmark concurrent simple RPC calls"""

    def run_test():
        async def concurrent_test():
            # Run 50 concurrent RPC calls with a limit of 10 at a time
            semaphore = asyncio.Semaphore(10)

            async def single_call():
                async with semaphore:
                    return await rpc_implementation.simple_call(42)

            tasks = [single_call() for _ in range(50)]
            return await asyncio.gather(*tasks)

        results = asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(concurrent_test(), timeout=120)
        )

        return results

    results = benchmark(run_test)

    # Check for exceptions in results
    for result in results:
        if isinstance(result, Exception):
            pytest.fail(f"RPC call failed with: {result}")

    # Verify correct return values
    for result in results:
        assert result == 84


def test_benchmark_stream_thousand(rpc_implementation, benchmark, event_loop):
    """Benchmark streaming 1000 values from RPC"""

    def run_test():
        async def collect():
            # No try/except - let exceptions propagate
            result = []
            try:
                async for x in rpc_implementation.stream_values(1000):
                    result.append(x)
                    if len(result) % 100 == 0:
                        await asyncio.sleep(0)  # Yield control periodically
            finally:
                logging.info(f"Stream test collected {len(result)} items before finishing/failing.")
            return result

        # No try/except - let exceptions fail the test
        return event_loop.run_until_complete(
            asyncio.wait_for(collect(), timeout=120)
        )

    result = benchmark(run_test)
    assert len(result) == 1000

