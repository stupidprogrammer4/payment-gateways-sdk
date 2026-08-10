from dataclasses import dataclass

from payment_gateways_sdk.common.data import GatewayDetails
from payment_gateways_sdk.common.exceptions import ConfigurationError


@dataclass(frozen=True)
class SadadConfig:
    """Sadad credentials. ``terminal_key`` is the base64 3DES key issued with the terminal."""

    merchant_id: str
    terminal_id: str
    terminal_key: str

    def __post_init__(self) -> None:
        missing = [
            name
            for name, value in (
                ("merchant_id", self.merchant_id),
                ("terminal_id", self.terminal_id),
                ("terminal_key", self.terminal_key),
            )
            if not str(value or "").strip()
        ]
        if missing:
            raise ConfigurationError(f"the sadad gateway needs {', '.join(missing)}")


@dataclass(frozen=True)
class SadadRequestDetails(GatewayDetails):
    """Everything Sadad reports when opening a payment."""

    res_code: int | None = None
    description: str | None = None
    token: str | None = None


@dataclass(frozen=True)
class SadadVerifyDetails(GatewayDetails):
    res_code: int | None = None
    description: str | None = None
    amount: int | None = None
    order_id: int | None = None
    retrival_ref_no: str | None = None
    system_trace_no: str | None = None
