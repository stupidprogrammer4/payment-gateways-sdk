"""The two gateways that need an optional dependency: Sadad (3DES) and Parsian (SOAP).

Neither ``pycryptodome`` nor ``zeep`` is a base dependency, so these tests cover the part that must
hold whether or not they are installed: importing the SDK works regardless, credentials are still
validated, and a missing dependency names itself instead of surfacing as an ImportError from
somewhere unrelated.
"""

import base64
import builtins
from collections.abc import Iterator
from typing import Any

import pytest

from payment_gateways_sdk import (
    ConfigurationError,
    DependencyError,
    ParsianAsync,
    ParsianSync,
    PaymentRequest,
    SadadAsync,
    SadadSync,
    available,
)
from payment_gateways_sdk.gateways.parsian import helpers as parsian_helpers
from payment_gateways_sdk.gateways.sadad import helpers as sadad_helpers

AMOUNT = 50_000
CALLBACK = "https://shop.example/callback"


@pytest.fixture
def hide_module(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """Make a named import fail, as it would on a host without the extra installed."""

    def hide(name: str) -> None:
        real_import = builtins.__import__

        def fake_import(module: str, *args: Any, **kwargs: Any) -> Any:
            if module == name or module.startswith(f"{name}."):
                raise ImportError(f"No module named {name!r}")
            return real_import(module, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

    yield hide


def test_the_package_imports_without_either_extra() -> None:
    """An ImportError at module scope would take every other gateway down with it."""
    assert "sadad" in available()
    assert "parsian" in available()


@pytest.mark.parametrize("gateway_cls", [SadadSync, SadadAsync])
def test_sadad_needs_all_three_credentials(gateway_cls: Any) -> None:
    with pytest.raises(ConfigurationError, match="terminal_key"):
        gateway_cls(merchant_id="m", terminal_id="t", terminal_key="")


@pytest.mark.parametrize("gateway_cls", [ParsianSync, ParsianAsync])
def test_parsian_needs_a_pin(gateway_cls: Any) -> None:
    with pytest.raises(ConfigurationError, match="pin"):
        gateway_cls(pin="")


def test_sadad_without_pycryptodome_raises_dependency_error(hide_module: Any) -> None:
    hide_module("Crypto")
    gateway = SadadSync(merchant_id="m", terminal_id="t", terminal_key="a" * 32)
    with pytest.raises(DependencyError, match="pycryptodome"):
        gateway.make_payment_request(
            PaymentRequest(amount=AMOUNT, callback_url=CALLBACK, order_id="1001")
        )


def test_parsian_without_zeep_raises_dependency_error(hide_module: Any) -> None:
    """A missing SOAP stack must name itself, and must not take any other gateway down with it."""
    parsian_helpers.clear_client_cache()
    hide_module("zeep")
    with pytest.raises(DependencyError, match="zeep"):
        ParsianSync(pin="PIN").make_payment_request(
            PaymentRequest(amount=AMOUNT, callback_url=CALLBACK, order_id="1001")
        )


def test_sadad_rejects_a_terminal_key_that_is_not_a_valid_3des_key() -> None:
    """A bad key must name itself rather than surfacing as a raw crypto error."""
    pytest.importorskip("Crypto", reason="needs the 'sadad' extra")
    config = SadadSync(merchant_id="m", terminal_id="t", terminal_key="not-base64!!").config
    with pytest.raises(ConfigurationError, match="terminal_key"):
        sadad_helpers.sign(config, "t;1001;50000")


def test_sadad_sign_is_deterministic_and_base64() -> None:
    """3DES-ECB with a fixed key has no IV, so the same input must give the same signature —
    which is what makes the verify call's SignData(Token) reproducible."""
    pytest.importorskip("Crypto", reason="needs the 'sadad' extra")
    key = base64.b64encode(bytes(range(24))).decode()
    config = SadadSync(merchant_id="m", terminal_id="t", terminal_key=key).config
    first = sadad_helpers.sign(config, "t;1001;50000")
    assert first == sadad_helpers.sign(config, "t;1001;50000")
    assert base64.b64decode(first)
