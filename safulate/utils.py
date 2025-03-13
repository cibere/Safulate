from typing import Callable
from inspect import signature


def split_list[T](original: list[T], key: Callable[[T], bool]) -> list[list[T]]:
    final: list[list[T]] = []
    temp: list[T] = []

    for item in original:
        if key(item):
            final.append(temp)
            temp = []
        else:
            temp.append(item)
    final.append(temp)

    return final


def ensure_kwargs[T: Callable](func: T) -> T:
    sig = signature(func)
    arg_annotations = {
        param.name: param.annotation for param in sig.parameters.values()
    }

    def wrapped(*args, **kwargs):
        for key, value in kwargs.items():
            annotation = arg_annotations[key]
            if value.__class__.__name__ != annotation:
                raise TypeError(
                    f"kwarg {key!r} type of {type(value)!r} did not match the expected type of {annotation!r}"
                )
        return func(*args, **kwargs)

    return wrapped  # pyright: ignore[reportReturnType]
