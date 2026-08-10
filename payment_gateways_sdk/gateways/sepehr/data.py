from dataclasses import dataclass

from payment_gateways_sdk.common.data import GatewayDetails
from payment_gateways_sdk.common.exceptions import ConfigurationError


@dataclass(frozen=True)
class SepehrConfig:
    """Sepehr credentials. ``terminal_id`` is the terminal number issued by the bank."""

    terminal_id: str

    def __post_init__(self) -> None:
        if not str(self.terminal_id or "").strip():
            raise ConfigurationError("the sepehr gateway needs a terminal_id")


@dataclass(frozen=True)
class SepehrTokenDetails(GatewayDetails):
    """Everything Sepehr reports when issuing a payment token."""

    status: int | None = None
    access_token: str | None = None
    terminal_id: str | None = None
    invoice_id: int | None = None


@dataclass(frozen=True)
class SepehrCallbackDetails(GatewayDetails):
    digital_receipt: str | None = None
    invoice_id: int | None = None
    amount: int | None = None
    rrn: str | None = None
    trace_number: str | None = None
    card_number: str | None = None
    issuer_bank: str | None = None
    date_paid: str | None = None
    response_code: str | None = None
    response_message: str | None = None


@dataclass(frozen=True)
class SepehrAdviceDetails(GatewayDetails):
    status: str | None = None
    return_id: int | None = None
    rrn: str | None = None
    trace_number: str | None = None
    card_number: str | None = None
    message: str | None = None
