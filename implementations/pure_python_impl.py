import asyncio
from typing import AsyncIterator
from interface import RPCImplementation

class PurePythonImplementation(RPCImplementation):
    """
    A baseline implementation that performs operations directly in Python
    without any RPC overhead, serialization, or network communication.
    """
    async def setup(self):
        """No setup required for direct Python calls."""
        pass

    async def teardown(self):
        """No teardown required for direct Python calls."""
        pass

    async def simple_call(self, value) -> object:
        """Directly performs the simple operation (multiply by 2)."""
        # Simulate the behavior of other implementations
        if isinstance(value, str):
            return value + value
        else:
            return value * 2

    async def stream_values(self, count: int) -> AsyncIterator[int]:
        """Directly yields the requested sequence of values."""
        for i in range(count):
            # Add a small async yield point, similar to how network libs might yield
            await asyncio.sleep(0) 
            yield i
