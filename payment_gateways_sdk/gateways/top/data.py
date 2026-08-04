"""Top / PNA (pay.top.ir) — credentials and the records Top itself returns.

Dataclasses only. Endpoints and fixed values live in ``constants.py``; the functions that build
payloads and read responses live in ``helpers.py``.

Contract (REST/JSON, HTTP Basic auth): POST ``/api/WPG/CreateOrder`` → ``status == 0`` +
``data.token`` + ``data.serviceURL``. Top hands back the payment page URL itself rather than a
template we can rebuild, so ``redirect_url`` comes from the response. POST
``/api/WPG/ConfirmPurchase`` ``{token, MerchantOrderId}`` → ``status == 0`` + ``data.rrn``.

Two traps worth knowing about:

* ``MerchantOrderId`` is a ``System.Int64``. A non-numeric value is rejected by Top's ASP.NET layer
  *before* Top's own code runs, and the response body carries no status and no message to explain
  it — so ``order_id`` is checked before the call goes out.
* Business failures come back as HTTP **200** with a status in the body, while a malformed request
  comes back as a 400 with no status at all. Neither the HTTP code nor the body alone is enough,
  which is why the transport decodes and the helpers read ``status``.

Amounts are in **Rial**, which is this SDK's unit, so they pass through unchanged.
"""

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
    """Everything Top reports when opening an order.

    ``service_url`` is Top's own payment page address. It is stored rather than rebuilt because
    Top does not publish a URL template — the address it hands back is the only one that works.
    """

    status: int | None = None
    message: str | None = None
    token: str | None = None
    service_url: str | None = None
    merchant_order_id: int | None = None


@dataclass(frozen=True)
class TopVerifyDetails(GatewayDetails):
    """Everything Top reports on confirmation.

    ``rrn`` is the Shaparak retrieval reference — the number that appears on the payer's statement
    and the one to quote in a dispute.
    """

    status: int | None = None
    message: str | None = None
    rrn: str | None = None
    amount: int | None = None
    card_number: str | None = None
    transaction_date: str | None = None
