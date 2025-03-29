import asyncio

TEST_RUN_COUNT = 0


def test_benchmark_concurrent_simple_call(rpc_implementation, benchmark, event_loop):

    def run_test():
        # Use the existing event loop from the fixture instead of creating a new one
        loop = event_loop

        async def concurrent_call():
            semaphore = asyncio.Semaphore(10)

            async def limited_call():
                async with semaphore:
                    return await rpc_implementation.simple_call(42)
            tasks = [limited_call() for _ in range(50)]
            return await asyncio.gather(*tasks)
        
        results = loop.run_until_complete(
            asyncio.wait_for(concurrent_call(), timeout=120))
        return results
        
    results = benchmark(run_test)
    # Check that we have at least some valid results
    valid_results = [r for r in results if r is not None]
    assert len(valid_results) > 0, "All RPC calls failed"
    # Check that all valid results are correct
    for result in valid_results:
        assert result == 84
