"""Parsian / PEC — credentials and the records the PEC services return.

Dataclasses only. Endpoints, SOAP namespaces and fixed values live in ``constants.py``; envelope
building and response reading live in ``helpers.py``.

Contract (SOAP 1.1 over ASMX): ``SalePaymentRequest{LoginAccount, OrderId, Amount, CallBackUrl}``
→ ``Status == 0`` and ``Token > 0`` → the customer goes to ``/NewIPG/?token=…``. The bank POSTs
back ``Token``, ``status`` and ``RRN``. ``ConfirmPayment{LoginAccount, Token}`` → ``Status == 0``.

**No SOAP library, and no WSDL round-trip.** ``zeep`` is synchronous — it has no async transport,
and even ``zeep.AsyncClient`` parses the WSDL while constructing the client — so using it meant
running the call in a worker thread and calling that async. The envelope is built directly instead
(see :mod:`payment_gateways_sdk.common.soap`), which makes the async engine genuinely async and
skips fetching a WSDL document to rediscover a two-operation contract that does not change.

``OrderId`` is a SOAP ``long``, so ``order_id`` must be numeric.

Amounts are in **Rial**, which is this SDK's unit, so they pass through unchanged.
"""

from dataclasses import dataclass

from payment_gateways_sdk.common.data import GatewayDetails
from payment_gateways_sdk.common.exceptions import ConfigurationError


@dataclass(frozen=True)
class ParsianConfig:
    """Parsian credentials. ``pin`` is the ``LoginAccount`` issued by the bank.

    ``proxy`` is optional and exists because PEC's endpoint is not always reachable directly. It is
    a credential rather than a constant so the gateway stays usable where no tunnel exists — a
    hardcoded proxy fails in a way that looks exactly like the bank being down. Any scheme
    the clients understand works; ``socks5://`` needs the ``socks`` extra.
    """

    pin: str
    proxy: str = ""

    def __post_init__(self) -> None:
        if not str(self.pin or "").strip():
            raise ConfigurationError("the parsian gateway needs a pin")


@dataclass(frozen=True)
class ParsianSaleDetails(GatewayDetails):
    """Everything the Sale service reports.

    ``token`` is a positive ``long``. PEC signals failure with ``Status != 0`` *and* also with a
    zero or negative token on some error paths, so both are checked.
    """

    status: int | None = None
    message: str | None = None
    token: int | None = None


@dataclass(frozen=True)
class ParsianConfirmDetails(GatewayDetails):
    """Everything the Confirm service reports.

    ``card_number_masked`` is the only place Parsian exposes the payer's card, and ``rrn`` is the
    Shaparak retrieval reference that appears on their statement.
    """

    status: int | None = None
    token: int | None = None
    rrn: str | None = None
    card_number_masked: str | None = None


@dataclass(frozen=True)
class ParsianCallbackDetails(GatewayDetails):
    """What the bank POSTs back to your callback.

    ``status`` here is the bank's own verdict, and a non-zero value means the payer cancelled or
    timed out. Confirming that would be asking Parsian to settle a transaction that never happened,
    so it is checked before the Confirm call goes out.
    """

    token: int | None = None
    status: int | None = None
    rrn: str | None = None
    order_id: int | None = None
    terminal_no: str | None = None
