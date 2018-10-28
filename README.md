# aiobuf

Experimental classes for asynchronous, batched logging.

## Usage

### `aiobuf.buffer.TimedLogBuffer`

Flushes buffer every nth second.

```python
import asyncio
from aiobuf.buffer import TimedLogBuffer
from aiobuf.format import timestamp


async def producer(log):
    for i in range(3):
        await asyncio.sleep(1)
        await log(f'message {i}')
    await log.close()


# buffer messages for two seconds
log = TimedLogBuffer(fn=print, buffer_time=2, formatter=timestamp)
tasks = producer(log), log.flush_loop()
loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(*tasks))
```

### `aiobuf.log.MaxSizeLogBuffer`

```python
import asyncio
import random

from aiobuf.buffer import MaxSizeLogBuffer
from aiobuf.format import timestamp


async def producer(log):
    for i in range(15):
        await asyncio.sleep(random.random() * 2 + 1)
        await log(f'message {i}')
    await log.close()


# Buffer messages .1 seconds or until the buffer exceeds 1024 bytes. Whichever
# occurs first triggers a flush.
log = MaxSizeLogBuffer(
    fn=print, max_size=1024, buffer_time=.1, formatter=timestamp)
tasks = producer(log), log.flush_loop()
asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
```
