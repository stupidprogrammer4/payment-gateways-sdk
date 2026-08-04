"""Sepehr / Mabna (بانک صادرات) — credentials and the records Sepehr itself returns.

Dataclasses only. Endpoints and fixed values live in ``constants.py``; the functions that build
payloads and read responses live in ``helpers.py``.

Contract (REST/JSON): POST ``/Rest/V1/PeymentApi/GetToken``
``{Amount, callbackURL, invoiceID, terminalID}`` → ``Status == 0`` + ``Accesstoken`` → the customer
goes to ``/Payment/Pay?token=…&terminalId=…``. The bank POSTs the result back as **form** data.
POST ``/Rest/V1/PeymentApi/Advice`` ``{digitalreceipt, Tid}`` → ``Status`` of ``ok`` or
``duplicate``, with ``ReturnId`` carrying the settled amount.

**Sepehr does not verify against the token it issued.** The Advice call takes ``digitalreceipt``,
which exists only in the bank's callback — so pass the callback payload through
:attr:`~payment_gateways_sdk.common.data.PaymentVerification.extra`. That is still safe: the
receipt only *selects* which transaction to ask about, and whether the money arrived is answered by
Sepehr's own API and checked against the amount you recorded. A replayed receipt can settle only
the payment it already belongs to, and only once.

``duplicate`` is a **success**: it is what Sepehr answers to the second Advice for the same
receipt, and a repeated callback for a paid transaction is still a paid transaction.

Amounts are in **Rial**, which is this SDK's unit, so they pass through unchanged.
"""

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
    """What the bank POSTs back to your callback, as form data.

    Sepehr is the one gateway whose callback carries data the verify call cannot get any other way
    — ``digital_receipt`` above all, which Advice is addressed by. The rest is descriptive, and is
    parsed here so a caller does not have to know that the bank lowercases its own field names.
    """

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
    """Everything Sepehr reports on Advice.

    ``return_id`` is Sepehr's name for the settled amount, not an identifier — the field that gets
    checked against the amount the payment was opened for.
    """

    status: str | None = None
    return_id: int | None = None
    rrn: str | None = None
    trace_number: str | None = None
    card_number: str | None = None
    message: str | None = None
