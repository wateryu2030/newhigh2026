"""Smoke tests: import key modules and call one entry point."""
import pytest


def test_core_import():
    from core import OHLCV, Position
    assert OHLCV is not None and Position is not None


def test_gateway_app_import():
    from gateway.app import app
    assert app is not None
