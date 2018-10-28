import asyncio
from typing import Callable, List


class BufferClosedError(RuntimeError):
    pass


class BufferNotFlushedError(RuntimeError):
    pass


class LogBuffer:
    """
    A buffer class that aggregates calls to a callable and stores the passed
    messages to concatenate them into one batched call when it's time to flush.
    The buffer can be initialized with a formatter that is called on the
    messages as they come in so that for instance a timestamping formatter will
    log the time of the occurring event as opposed to the time of flushing.
    """
    def __init__(
            self,
            fn: Callable,
            formatter: Callable = None):
        self._fn = fn
        self._formatter = formatter
        self._buffer: List[str] = []
        self._open = True
        self._flush_lock = asyncio.Lock()

    async def flush(self) -> None:
        if not self._buffer:
            return
        async with self._flush_lock:
            self._fn('\n'.join(self._buffer))
            self._buffer = []

    async def __call__(self, message: str) -> None:
        if self._formatter is not None:
            message = self._formatter(message)
        async with self._flush_lock:
            if not self._open:
                raise BufferClosedError(
                    "Trying to write to a closed buffer")
            self._buffer.append(message)

    async def close(self) -> None:
        async with self._flush_lock:
            self._open = False

    def __del__(self):
        if self._buffer:
            raise BufferNotFlushedError(
                "A buffer object was deconstructed with messages not yet "
                "flushed")


class TimedLogBuffer(LogBuffer):
    """
    This class extends the LogBuffer with the ability to flush messages every
    nth second.
    """

    def __init__(
            self,
            fn: Callable,
            buffer_time: float = .1,
            formatter: Callable = None):
        super().__init__(fn, formatter)
        self._buffer_time = buffer_time

    async def flush_loop(self) -> None:
        while self._open:
            await self.flush()
            await asyncio.sleep(self._buffer_time)
        await self.flush()


class MaxSizeLogBuffer(TimedLogBuffer):
    """
    Keeps track of the size of its buffered messages and flushes when either the
    size or the time exceeds the given maximums. This buffer has more CPU
    overhead than the TimedLogBuffer because it has to count the size of each
    message and keep track of a running total.
    """

    def __init__(
            self,
            fn: Callable,
            buffer_time: float = .2,
            max_size: int = 120,
            formatter: Callable = None):
        super().__init__(fn, buffer_time, formatter)
        self._max_size = max_size
        self._size = 0
        self.SizeExceeded = asyncio.Event()

    async def __call__(self, message: str) -> None:
        if self._formatter is not None:
            message = self._formatter(message)
        async with self._flush_lock:
            if not self._open:
                raise BufferClosedError(
                    "Trying to write to a closed buffer")
            self._buffer.append(message)
            self._size += len(message.encode('utf-8'))
        if self._size > self._max_size:
            self.SizeExceeded.set()

    async def flush_loop(self) -> None:
        """
        Flushing loop that can run in the background. Wait a given amount of
        time between flushes. If the maximum size limit is exceeded during that
        time, we flush.
        """
        while self._open:
            try:
                await asyncio.wait_for(
                    self.SizeExceeded.wait(), self._buffer_time)
                await self('[flusher] maximum buffer size exceeded')
            except asyncio.TimeoutError:
                await self('[flusher] maximum buffer time exceeded')
                pass
            await self.flush()
        await self.flush()

    async def flush(self) -> None:
        if not self._buffer:
            return
        async with self._flush_lock:
            self._fn('\n'.join(self._buffer))
            self._buffer = []
            self._size = 0
            self.SizeExceeded.clear()
