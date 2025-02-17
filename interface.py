import abc
from typing import AsyncIterator

class RPCImplementation(abc.ABC):
    @abc.abstractmethod
    async def setup(self):
        """Set up the RPC implementation, including starting any servers or connections."""
        pass

    @abc.abstractmethod
    async def teardown(self):
        """Tear down and clean up any resources used by the RPC implementation."""
        pass

    @abc.abstractmethod
    async def simple_call(self, value) -> object:
        """Make a simple RPC call that multiplies the input value by 2."""
        pass

    @abc.abstractmethod
    async def stream_values(self, count: int) -> AsyncIterator[int]:
        """Return an asynchronous iterator yielding integer values from 0 to count-1."""
        pass
