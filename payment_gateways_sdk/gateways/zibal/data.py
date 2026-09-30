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


@dataclass(frozen=True)
class ZibalCardConfig:
    merchant: str = SANDBOX_MERCHANT
    check_mobile_with_card: bool = True


@dataclass(frozen=True)
class ZibalInquiryDetails(GatewayDetails):
    result: int | None = None
    status: int | None = None
    order_id: str | None = None
    amount: int | None = None
    ref_number: str | None = None
    paid_at: str | None = None
    verified_at: str | None = None
