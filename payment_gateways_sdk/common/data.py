from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GatewayDetails:
    pass


@dataclass(frozen=True)
class PaymentRequest:
    """What you hand a gateway to open a payment."""

    amount: int
    """Amount in Rial."""

    callback_url: str
    """Where the gateway returns the customer once they are done paying."""

    order_id: str = ""

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
class CardPaymentRequest(PaymentRequest):
    card_pan: str = ""
    national_id: str = ""


@dataclass(frozen=True)
class PaymentVerification:
    """What you hand a gateway to confirm a payment after the customer comes back."""

    authority: str

    amount: int

    order_id: str = ""
    """Your reference. Required by Top, whose confirm call is scoped to (token, order id)."""

    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationResult:
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

    def __bool__(self) -> bool:
        return self.success
