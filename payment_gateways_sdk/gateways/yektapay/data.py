from dataclasses import dataclass

from payment_gateways_sdk.common.data import GatewayDetails
from payment_gateways_sdk.common.exceptions import ConfigurationError


@dataclass(frozen=True)
class YektapayConfig:
    """Yektapay credentials. ``token`` is the merchant API token from your panel."""

    token: str

    def __post_init__(self) -> None:
        if not str(self.token or "").strip():
            raise ConfigurationError("the yektapay gateway needs a token")


@dataclass(frozen=True)
class YektapayOrderDetails(GatewayDetails):
    """Everything Yektapay reports when opening an order."""

    uuid: str | None = None
    amount: int | None = None
    title: str | None = None
    status: str | None = None
    callback_url: str | None = None
    created_at: str | None = None


@dataclass(frozen=True)
class YektapayVerifyDetails(GatewayDetails):
    """Everything Yektapay reports on verification."""

    uuid: str | None = None
    status: str | None = None
    amount: int | None = None
    reference: str | None = None
    card_number: str | None = None
    paid_at: str | None = None
    description: str | None = None
