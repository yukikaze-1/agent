# Project:      Agent
# Author:       yomu
# Time:         2024/6/20
# Version:      0.1
# Description:  Tool functions

"""
    各种杂七杂八的工具函数
"""

from typing import Callable, TypeVar, Awaitable, cast, NoReturn
import asyncio
import functools

T = TypeVar("T")

def retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    on_failure: Callable[[BaseException], None] | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            _delay = delay
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == retries - 1:
                        if on_failure:
                            on_failure(e)
                        raise e  # 明确 raise 后终止
                    await asyncio.sleep(_delay)
                    _delay *= backoff
            assert False, "Unreachable"  # 避免类型推导器报错
        return wrapper
    return decorator

# import time
# import functools
# import asyncio
# import inspect
# from typing import Callable, Tuple, Type, Any, Optional, Union


# def retry(retries: int = 3, delay: float = 1.0, backoff: float = 2.0,
#           exceptions: Tuple[Type[Exception]] = (Exception,),
#           on_failure: Optional[Callable[[BaseException], None]] = None):
#     """
#     通用的重试装饰器，支持同步和异步函数。

#     :param retries: 最大重试次数
#     :param delay: 初始重试间隔（秒）
#     :param backoff: 每次重试延迟的倍数增长（指数退避）
#     :param exceptions: 可重试的异常类型
#     :param on_failure: 最终失败回调，接收最后的异常对象
#     """
#     def decorator(func: Callable):
#         # 包装异步函数
#         @functools.wraps(func)
#         async def async_wrapper(*args, **kwargs):
#             _delay = delay
#             for attempt in range(retries):
#                 try:
#                     return await func(*args, **kwargs)
#                 except exceptions as e:
#                     if attempt == retries - 1:
#                         if on_failure:
#                             on_failure(e)
#                         raise
#                     await asyncio.sleep(_delay)
#                     _delay *= backoff

#         # 包装同步函数
#         @functools.wraps(func)
#         def sync_wrapper(*args, **kwargs):
#             _delay = delay
#             for attempt in range(retries):
#                 try:
#                     return func(*args, **kwargs)
#                 except exceptions as e:
#                     if attempt == retries - 1:
#                         if on_failure:
#                             on_failure(e)
#                         raise
#                     time.sleep(_delay)
#                     _delay *= backoff

#         # 更稳健地判断是否为异步函数（兼容类方法）
#         if inspect.iscoroutinefunction(func) or inspect.iscoroutinefunction(getattr(func, '__func__', None)):
#             return async_wrapper
#         return sync_wrapper

#     return decorator


