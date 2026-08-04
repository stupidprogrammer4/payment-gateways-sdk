"""Sadad (بانک ملی) — credentials and the records Sadad itself returns.

Dataclasses only. Endpoints and fixed values live in ``constants.py``; signing, payload building
and response reading live in ``helpers.py``.

Contract (REST/JSON): every request carries ``SignData``, a 3DES-ECB encryption of a
semicolon-joined string under the terminal key, base64 on both ends. POST
``/VPG/api/v0/Request/PaymentRequest``
``{MerchantId, TerminalId, Amount, OrderId, LocalDateTime, ReturnUrl, SignData}`` →
``ResCode == 0`` + ``Token`` → the customer goes to ``/VPG/Purchase?Token=…``. POST
``/VPG/api/v0/Advice/Verify`` ``{Token, SignData(Token)}`` → ``ResCode == 0`` + ``Amount`` +
``RetrivalRefNo``.

**Optional dependency.** 3DES has no stdlib equivalent, so this gateway needs ``pycryptodome``::

    pip install "payment-gateways-sdk[sadad]"

It is imported lazily and its absence raises
:class:`~payment_gateways_sdk.common.exceptions.DependencyError`. An ImportError at module scope
would break every *other* gateway too, so a deployment that never configured Sadad would lose Zibal
alongside it.

Amounts are in **Rial**, which is this SDK's unit, so they pass through unchanged.
"""

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
    """Everything Sadad reports on verification.

    ``retrival_ref_no`` keeps the bank's own spelling of "retrieval" — renaming it here would make
    the field impossible to match against Sadad's documentation and its support tooling.
    """

    res_code: int | None = None
    description: str | None = None
    amount: int | None = None
    order_id: int | None = None
    retrival_ref_no: str | None = None
    system_trace_no: str | None = None
