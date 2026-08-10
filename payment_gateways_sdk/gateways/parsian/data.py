from dataclasses import dataclass

from payment_gateways_sdk.common.data import GatewayDetails
from payment_gateways_sdk.common.exceptions import ConfigurationError


@dataclass(frozen=True)
class ParsianConfig:
    pin: str
    proxy: str = ""
    aes_key: str = ""
    aes_iv: str = ""

    def __post_init__(self) -> None:
        if not str(self.pin or "").strip():
            raise ConfigurationError("the parsian gateway needs a pin")


@dataclass(frozen=True)
class ParsianSaleDetails(GatewayDetails):
    status: int | None = None
    message: str | None = None
    token: int | None = None


@dataclass(frozen=True)
class ParsianConfirmDetails(GatewayDetails):
    status: int | None = None
    token: int | None = None
    rrn: str | None = None
    card_number_masked: str | None = None


@dataclass(frozen=True)
class ParsianCallbackDetails(GatewayDetails):
    token: int | None = None
    status: int | None = None
    rrn: str | None = None
    order_id: int | None = None
    terminal_no: str | None = None
