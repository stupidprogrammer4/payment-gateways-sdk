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
    code: int | None = None
    message: str | None = None
    authority: str | None = None
    fee_type: str | None = None
    fee: int | None = None


@dataclass(frozen=True)
class ZarinpalVerifyDetails(GatewayDetails):
    code: int | None = None
    message: str | None = None
    ref_id: str | None = None
    card_pan: str | None = None
    card_hash: str | None = None
    fee_type: str | None = None
    fee: int | None = None
    shaparak_fee: int | None = None
    order_id: str | None = None
