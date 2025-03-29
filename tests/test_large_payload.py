import asyncio


TEST_RUN_COUNT = 0


def test_benchmark_large_payload(rpc_implementation, benchmark, event_loop):
    """Benchmark the simple_call RPC for large payloads with concurrent calls."""

    def run_test():
        # Use the existing event loop from the fixture instead of creating a new one
        loop = event_loop

        async def concurrent_payload():
            sizes = [1024, 10*1024, 100*1024, 1024*1024]

            async def call_payload(size):
                payload = "x" * size
                result = await rpc_implementation.simple_call(payload)
                return (size, result)
            tasks = [call_payload(size) for size in sizes]
            results = await asyncio.gather(*tasks)
            return results
        
        results = loop.run_until_complete(
            asyncio.wait_for(concurrent_payload(), timeout=180))
        return results
        
    results = benchmark(run_test)
    # Check that we have at least some valid results
    valid_results = [(size, res) for size, res in results if res is not None]
    assert len(valid_results) > 0, "All RPC calls failed"
    # Check that all valid results are correct
    for size, res in valid_results:
        assert len(res) == 2 * size
