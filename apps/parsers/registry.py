"""
Registry mapping a Customer.parser_key string to a concrete BasePOParser
implementation. Parser modules register themselves via the @register
decorator; apps/parsers/apps.py imports them at startup so the decorators run.
"""
from .base import BasePOParser

_REGISTRY: dict[str, type[BasePOParser]] = {}


def register(key: str):
    def _decorator(cls: type[BasePOParser]):
        _REGISTRY[key] = cls
        return cls
    return _decorator


def get_parser(key: str) -> BasePOParser:
    try:
        return _REGISTRY[key]()
    except KeyError:
        raise KeyError(
            f"No parser registered for key '{key}'. "
            f"Known keys: {sorted(_REGISTRY)}"
        )
