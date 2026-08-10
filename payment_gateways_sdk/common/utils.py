"""The checks and coercions every gateway needs, written once so they cannot drift apart."""

from typing import Any

from payment_gateways_sdk.common.exceptions import ConfigurationError


def as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_text(value: Any) -> str | None:
    """An optional string field, stripped, or ``None`` when empty."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalized_pan(card_pan: str, *, gateway: str) -> str:
    digits = "".join(ch for ch in str(card_pan or "") if ch.isdigit())
    if not digits:
        raise ConfigurationError(f"the {gateway} gateway needs a card_pan for a card payment")
    if len(digits) != 16:
        raise ConfigurationError(
            f"the {gateway} gateway needs a 16-digit card_pan; got {len(digits)} digits"
        )
    return digits


def numeric_order_id(order_id: str, *, gateway: str) -> int:
    text = str(order_id or "").strip()
    if not text:
        raise ConfigurationError(
            f"the {gateway} gateway needs a numeric order_id, and none was set"
        )
    try:
        return int(text)
    except ValueError as exc:
        raise ConfigurationError(
            f"the {gateway} gateway needs a numeric order_id; got {order_id!r}"
        ) from exc


def check_amount(
    settled: Any, expected: int, *, gateway: str, required: bool
) -> tuple[int, str | None]:
    if settled is None:
        if required:
            return expected, f"{gateway} reported no amount — cannot confirm what was paid"
        return expected, None
    try:
        settled_int = int(settled)
    except (TypeError, ValueError):
        return expected, f"{gateway} reported a non-integer amount: {settled!r}"
    if settled_int != expected:
        return settled_int, f"amount mismatch: gateway {settled_int} != expected {expected}"
    return settled_int, None
