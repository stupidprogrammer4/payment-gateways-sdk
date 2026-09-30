from dataclasses import dataclass

from payment_gateways_sdk.common.data import GatewayDetails
from payment_gateways_sdk.common.exceptions import ConfigurationError


@dataclass(frozen=True)
class TopConfig:
    """Top credentials — the Basic-auth pair from your merchant panel."""

    username: str
    password: str

    def __post_init__(self) -> None:
        missing = [
            name
            for name, value in (("username", self.username), ("password", self.password))
            if not str(value or "").strip()
        ]
        if missing:
            raise ConfigurationError(f"the top gateway needs {', '.join(missing)}")


@dataclass(frozen=True)
class TopRequestDetails(GatewayDetails):
    status: int | None = None
    message: str | None = None
    token: str | None = None
    service_url: str | None = None
    merchant_order_id: int | None = None


@dataclass(frozen=True)
class TopVerifyDetails(GatewayDetails):
    status: int | None = None
    message: str | None = None
    rrn: str | None = None
    amount: int | None = None
    card_number: str | None = None
    transaction_date: str | None = None


@dataclass(frozen=True)
class TopInquiryDetails(GatewayDetails):
    status: int | None = None
    result_id: int | None = None
    amount: int | None = None
    transaction_id: str | None = None
    result_description: str | None = None
