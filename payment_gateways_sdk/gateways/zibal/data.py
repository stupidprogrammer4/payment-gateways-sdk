"""Zibal — credentials and the records Zibal itself returns.

Dataclasses only. Endpoints and fixed values live in ``constants.py``; the functions that build
payloads and read responses live in ``helpers.py``.

Contract (REST/JSON): POST ``/v1/request`` ``{merchant, amount, callbackUrl, orderId}`` →
``result == 100`` + ``trackId`` → the customer goes to ``/start/{trackId}``. The callback carries
``trackId`` back. POST ``/v1/verify`` ``{merchant, trackId}`` → ``result`` 100 = paid (with
``refNumber`` and ``amount``), 201 = already verified.

Sandbox: merchant ``"zibal"`` auto-succeeds and moves no real money — the default here, so a first
run needs no credentials at all.

Amounts are in **Rial**, which is this SDK's unit, so they pass through unchanged.
"""

from dataclasses import dataclass

from payment_gateways_sdk.common.data import GatewayDetails
from payment_gateways_sdk.gateways.zibal.constants import SANDBOX_MERCHANT


@dataclass(frozen=True)
class ZibalConfig:
    """Zibal credentials. ``merchant`` is the merchant code from your panel."""

    merchant: str = SANDBOX_MERCHANT


@dataclass(frozen=True)
class ZibalRequestDetails(GatewayDetails):
    """Everything Zibal reports when opening a payment."""

    result: int | None = None
    message: str | None = None
    track_id: int | None = None


@dataclass(frozen=True)
class ZibalVerifyDetails(GatewayDetails):
    """Everything Zibal reports on verification.

    ``status`` is Zibal's transaction state, decoded into ``status_text`` via
    :data:`~payment_gateways_sdk.gateways.zibal.constants.PAYMENT_STATUSES`. ``wage`` is the
    commission Zibal took, which is why the merchant's settlement can be smaller than ``amount``
    without anything being wrong.
    """

    result: int | None = None
    message: str | None = None
    amount: int | None = None
    status: int | None = None
    status_text: str | None = None
    paid_at: str | None = None
    card_number: str | None = None
    ref_number: str | None = None
    order_id: str | None = None
    description: str | None = None
    wage: int | None = None
