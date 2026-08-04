"""Test suite for payment-gateways-sdk.

This file makes ``tests`` a package so ``conftest.py`` resolves under exactly one module name.
Without it, pytest imports it as ``conftest`` while the test modules import ``tests.conftest``,
and a type checker sees the same file twice under two names.
"""
