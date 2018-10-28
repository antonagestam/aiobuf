import datetime
import functools
from typing import Union, Callable


def format_message(message: Union[str, bytes], formatter: Callable) -> str:
    if isinstance(message, bytes):
        message = message.decode('utf-8')
    return '\n'.join(formatter(line) for line in message.split('\n'))


def formatter(fn: Callable) -> Callable:
    """
    Use this decorator to define logging formatters. The decorated function
    should accept a single line string as its first argument and return the
    formatted line. The decorator returns a partial of the format_message
    function which handles converting bytes to str and iteration over lines in a
    log message.
    """
    return functools.wraps(fn)(functools.partial(format_message, formatter=fn))


def create_timestamp_formatter(
        time_fn: Callable,
        time_format: str = '%Y-%m-%d %H:%M:%S') -> Callable:
    @formatter
    def timestamp_format(line: str) -> str:
        return f'[{time_fn():{time_format}}]: {line}'
    return timestamp_format


timestamp = create_timestamp_formatter(datetime.datetime.now)
