"""The checks and coercions every gateway needs, written once so they cannot drift apart."""

from typing import Any

from payment_gateways_sdk.common.exceptions import ConfigurationError


def as_int(value: Any) -> int | None:
    """An optional integer field, or ``None`` when the gateway omitted it or sent nonsense.

    Detail records are descriptive, not decisive — nothing settles on them — so a field that
    arrives as ``"12,000"`` or ``""`` is reported as missing rather than raising. The values that
    *do* decide whether money moved go through :func:`check_amount`, which fails loudly instead.
    """
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


def numeric_order_id(order_id: str, *, gateway: str) -> int:
    """The order reference as an integer, for gateways whose order field is a 64-bit int.

    Fails here rather than at the gateway. Top's ``MerchantOrderId`` is a ``System.Int64`` and a
    non-numeric value is rejected by its ASP.NET layer *before* Top's own code runs, with a body
    that carries no status and no message — the payer sees "unknown error" and the log says
    nothing. Sepehr, Sadad and Parsian have the same shape.
    """
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
    """Compare a gateway's settled amount against the amount the payment was opened for.

    Returns ``(amount, reason)``: the amount to report, and why it failed — ``None`` when it did
    not. The amount falls back to ``expected`` for the gateways that report none, so a caller never
    has to re-parse a value this function has already validated.

    ``required=True`` fails closed when the gateway reports no amount at all: a gateway that says
    "paid" without saying how much is the one case that cannot be reasoned about, and letting it
    through unchecked makes it the single case that settles unverified. It is ``False`` only for
    the gateways whose verify response has no amount field by design — for those, what binds the
    answer to this payment is that the call is scoped to a token we issued.
    """
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
