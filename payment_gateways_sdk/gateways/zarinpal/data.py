"""ZarinPal — credentials and the records ZarinPal itself returns.

Dataclasses only. Endpoints and fixed values live in ``constants.py``; the functions that build
payloads and read responses live in ``helpers.py``.

Contract (PG v4, REST/JSON): POST ``/pg/v4/payment/request.json``
``{merchant_id, amount, description, callback_url}`` → ``data.code == 100`` + ``data.authority``
→ the customer goes to ``/pg/StartPay/{authority}``. The callback returns ``Authority`` and
``Status``. POST ``/pg/v4/payment/verify.json`` ``{merchant_id, amount, authority}`` →
``data.code`` 100 = paid, 101 = already verified.

Amounts are in **Rial**, which is this SDK's unit, so they pass through unchanged.
"""

from dataclasses import dataclass

from payment_gateways_sdk.common.data import GatewayDetails
from payment_gateways_sdk.common.exceptions import ConfigurationError


@dataclass(frozen=True)
class ZarinpalConfig:
    """ZarinPal credentials. ``merchant_id`` is the 36-character UUID from your panel."""

    merchant_id: str
    sandbox: bool = False
    """Route to ZarinPal's sandbox host, which settles nothing and moves no money."""

    def __post_init__(self) -> None:
        if not str(self.merchant_id or "").strip():
            raise ConfigurationError("the zarinpal gateway needs a merchant_id")


@dataclass(frozen=True)
class ZarinpalRequestDetails(GatewayDetails):
    """Everything ZarinPal reports when opening a payment.

    The fee fields are ZarinPal's own: ``fee_type`` says who pays the gateway's commission
    (``Merchant`` or ``Payer``), which decides whether the payer is charged ``amount`` or
    ``amount + fee``. Nothing here changes what the SDK settles; it is what ZarinPal will show.
    """

    code: int | None = None
    message: str | None = None
    authority: str | None = None
    fee_type: str | None = None
    fee: int | None = None


@dataclass(frozen=True)
class ZarinpalVerifyDetails(GatewayDetails):
    """Everything ZarinPal reports on verification.

    ``card_pan`` is masked at ZarinPal's end, and ``card_hash`` is a stable SHA-256 of the full PAN
    — the field to key on if you need "same card as last time" without ever holding a card number.
    """

    code: int | None = None
    message: str | None = None
    ref_id: str | None = None
    card_pan: str | None = None
    card_hash: str | None = None
    fee_type: str | None = None
    fee: int | None = None
    shaparak_fee: int | None = None
    order_id: str | None = None
