"""Value objects shared by every gateway, in both engines.

Amounts are always in **Rial**. Every Iranian IPG in this SDK is denominated in Rial, so no unit
conversion happens anywhere; if you keep Toman in your own domain, multiply by 10 before calling.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GatewayDetails:
    """Base for the per-gateway detail records.

    The fields below are the common denominator across seven gateways, which is deliberately not
    all any one of them reports. Each gateway defines its own subclass in its ``data.py`` carrying
    everything *that* gateway returns — ZarinPal's fee breakdown and masked card hash, Zibal's
    ``paidAt`` and issuing bank, Sadad's retrieval reference — so nothing is lost to the shared
    shape. They arrive on ``PaymentResponse.details`` and ``VerificationResult.details``, typed, so
    reading gateway-specific data does not mean digging through ``raw``.
    """


@dataclass(frozen=True)
class PaymentRequest:
    """What you hand a gateway to open a payment."""

    amount: int
    """Amount in Rial."""

    callback_url: str
    """Where the gateway returns the customer once they are done paying."""

    order_id: str = ""
    """Your own reference for this payment.

    Some gateways (Top, Sepehr, Sadad, Parsian) require this to be numeric — they declare their
    field as a 64-bit integer and reject anything else before their own code runs. Those gateways
    raise :class:`~payment_gateways_sdk.common.exceptions.ConfigurationError` on a non-numeric
    value rather than letting the gateway answer with an error that explains none of it.
    """

    description: str = ""
    """Shown to the payer, and on their bank statement where the gateway supports it."""

    mobile: str = ""
    """Optional payer mobile number; gateways that accept it pre-fill the payment page."""


@dataclass(frozen=True)
class PaymentResponse:
    """The gateway's answer to a payment request."""

    authority: str
    """The gateway's token for this payment. Store it — verification needs it back."""

    redirect_url: str
    """Send the customer here to pay."""

    raw: dict[str, Any] = field(default_factory=dict)
    """The gateway's decoded response, untouched, for logging and support tickets."""

    details: GatewayDetails | None = None
    """Everything this particular gateway reported, as its own typed record."""


@dataclass(frozen=True)
class PaymentVerification:
    """What you hand a gateway to confirm a payment after the customer comes back."""

    authority: str
    """The token from :class:`PaymentResponse`, as *you* stored it — never a value read from the
    callback query string. This is what binds the answer to the payment you actually opened."""

    amount: int
    """The amount in Rial you recorded when opening the payment. Gateways that echo a settled
    amount are checked against this, and a mismatch fails verification."""

    order_id: str = ""
    """Your reference. Required by Top, whose confirm call is scoped to (token, order id)."""

    extra: dict[str, Any] = field(default_factory=dict)
    """Fields the gateway needs that only exist in its callback.

    Sepehr verifies against the ``digitalreceipt`` the bank POSTs back rather than the token it
    issued, and Parsian reads ``status`` and ``RRN`` from the callback. Pass the callback payload
    through here for those two; every other gateway ignores it.
    """


@dataclass(frozen=True)
class VerificationResult:
    """The outcome of a verification. Never raises for a declined payment — a customer returning
    from their bank must not meet an exception, and a failure here is a state you can retry from."""

    success: bool
    """Whether the money actually arrived."""

    reference: str | None = None
    """The settlement reference on success — what appears on the bank statement."""

    amount: int | None = None
    """The settled amount in Rial, where the gateway reports one."""

    message: str | None = None
    """Why it failed. ``None`` on success."""

    raw: dict[str, Any] = field(default_factory=dict)
    """The gateway's decoded response, untouched."""

    details: GatewayDetails | None = None
    """Everything this particular gateway reported, as its own typed record — the masked card
    number, the settlement time, the fee, whatever that gateway sends."""

    def __bool__(self) -> bool:
        return self.success
