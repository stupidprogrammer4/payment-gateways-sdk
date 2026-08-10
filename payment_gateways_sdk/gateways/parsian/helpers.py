import base64
import json
from typing import Any

from payment_gateways_sdk.common.data import (
    CardPaymentRequest,
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)
from payment_gateways_sdk.common.exceptions import (
    ConfigurationError,
    DependencyError,
    GatewayError,
)
from payment_gateways_sdk.common.utils import (
    as_int,
    as_text,
    normalized_pan,
    numeric_order_id,
)
from payment_gateways_sdk.gateways.parsian.constants import (
    CARD_RESTRICTION_FIELD,
    NAME,
    REDIRECT_URL,
    SUCCESS_STATUS,
)
from payment_gateways_sdk.gateways.parsian.data import (
    ParsianCallbackDetails,
    ParsianConfig,
    ParsianConfirmDetails,
    ParsianSaleDetails,
)

_sync_clients: dict[tuple[str, str], Any] = {}
_async_clients: dict[tuple[str, str], Any] = {}


def _require_zeep() -> Any:
    try:
        import zeep  # noqa: PLC0415 — lazy so a missing SOAP stack takes out only this gateway
    except ImportError as exc:
        raise DependencyError(
            "the parsian gateway needs SOAP support from 'zeep' — "
            "install it with: pip install 'payment-gateways-sdk[parsian]'"
        ) from exc
    return zeep


def sync_client(config: ParsianConfig, wsdl: str) -> Any:
    """A cached :class:`zeep.Client`. Blocking: it fetches and parses the WSDL on first use."""
    proxy = config.proxy.strip()
    key = (wsdl, proxy)
    cached = _sync_clients.get(key)
    if cached is not None:
        return cached

    zeep = _require_zeep()
    transport = None
    if proxy:
        import requests  # noqa: PLC0415 — only needed when a proxy is configured

        session = requests.Session()
        session.proxies = {"http": proxy, "https": proxy}
        transport = zeep.transports.Transport(session=session)
    client = zeep.Client(wsdl, transport=transport) if transport else zeep.Client(wsdl)
    _sync_clients[key] = client
    return client


def async_client(config: ParsianConfig, wsdl: str) -> Any:
    proxy = config.proxy.strip()
    key = (wsdl, proxy)
    cached = _async_clients.get(key)
    if cached is not None:
        return cached

    zeep = _require_zeep()
    try:
        from zeep.transports import AsyncTransport  # noqa: PLC0415 — part of the `async` extra
    except ImportError as exc:
        raise DependencyError(
            "the parsian async engine needs zeep's async transport — "
            "install it with: pip install 'payment-gateways-sdk[parsian]'"
        ) from exc

    transport: Any = None
    if proxy:
        import httpx  # noqa: PLC0415 — zeep's async transport is built on httpx

        transport = AsyncTransport(client=httpx.AsyncClient(proxy=proxy))
    client = zeep.AsyncClient(wsdl, transport=transport) if transport else zeep.AsyncClient(wsdl)
    _async_clients[key] = client
    return client


def clear_client_cache() -> None:
    """Drop every cached client. Used by the tests, which point each case at a fresh WSDL."""
    _sync_clients.clear()
    _async_clients.clear()


def redirect_url(token: int) -> str:
    return REDIRECT_URL.format(token=token)


def build_sale_request(config: ParsianConfig, data: PaymentRequest) -> dict[str, Any]:
    return {
        "LoginAccount": config.pin.strip(),
        "Amount": data.amount,
        "OrderId": numeric_order_id(data.order_id, gateway=NAME),
        "CallBackUrl": data.callback_url,
        "AdditionalData": data.description or "",
        "Originator": data.mobile or "",
    }


def encrypt_pan(config: ParsianConfig, card_pan: str) -> str:
    if not (config.aes_key.strip() and config.aes_iv.strip()):
        raise ConfigurationError("the parsian gateway needs aes_key and aes_iv for a card payment")
    try:
        from Crypto.Cipher import AES  # noqa: PLC0415
        from Crypto.Util.Padding import pad  # noqa: PLC0415
    except ImportError as exc:
        raise DependencyError(
            "parsian card payments need AES from 'pycryptodome' — "
            "install it with: pip install 'payment-gateways-sdk[card]'"
        ) from exc
    digits = normalized_pan(card_pan, gateway=NAME)
    try:
        cipher = AES.new(
            base64.b64decode(config.aes_key.strip()),
            AES.MODE_CBC,
            base64.b64decode(config.aes_iv.strip()),
        )
        encrypted = cipher.encrypt(pad(digits.encode("utf-8"), AES.block_size))
    except Exception as exc:
        raise ConfigurationError(
            f"parsian could not encrypt the card — are aes_key and aes_iv valid base64? {exc}"
        ) from exc
    return base64.b64encode(encrypted).decode("utf-8")


def build_card_sale_request(config: ParsianConfig, data: CardPaymentRequest) -> dict[str, Any]:
    request = build_sale_request(config, data)
    request["AdditionalData"] = json.dumps(
        [{CARD_RESTRICTION_FIELD: encrypt_pan(config, data.card_pan)}]
    )
    return request


def build_confirm_request(config: ParsianConfig, token: int) -> dict[str, Any]:
    return {"LoginAccount": config.pin.strip(), "Token": token}


def read_sale_details(result: Any) -> ParsianSaleDetails:
    """``zeep`` hands back a typed object, so the fields are read as attributes."""
    return ParsianSaleDetails(
        status=as_int(getattr(result, "Status", None)),
        message=as_text(getattr(result, "Message", None)),
        token=as_int(getattr(result, "Token", None)),
    )


def parse_sale_result(result: Any) -> PaymentResponse:
    details = read_sale_details(result)
    if details.status != SUCCESS_STATUS or not details.token or details.token <= 0:
        raise GatewayError(
            f"parsian declined the request: {details.message} (status {details.status})",
            code=details.status,
        )
    return PaymentResponse(
        authority=str(details.token),
        redirect_url=redirect_url(details.token),
        details=details,
    )


def read_confirm_details(result: Any) -> ParsianConfirmDetails:
    return ParsianConfirmDetails(
        status=as_int(getattr(result, "Status", None)),
        token=as_int(getattr(result, "Token", None)),
        rrn=as_text(getattr(result, "RRN", None)),
        card_number_masked=as_text(getattr(result, "CardNumberMasked", None)),
    )


def parse_confirm_result(result: Any, data: PaymentVerification) -> VerificationResult:
    details = read_confirm_details(result)
    if details.status != SUCCESS_STATUS:
        return VerificationResult(
            success=False, message=f"parsian declined: {details.status}", details=details
        )
    rrn = details.rrn or read_callback(data.extra).rrn
    return VerificationResult(
        success=True,
        reference=str(rrn or data.authority),
        amount=data.amount,
        details=details,
    )


def read_callback(params: dict[str, Any]) -> ParsianCallbackDetails:
    lowered = {str(key).lower(): value for key, value in params.items()}
    return ParsianCallbackDetails(
        token=as_int(lowered.get("token")),
        status=as_int(lowered.get("status")),
        rrn=as_text(lowered.get("rrn")),
        order_id=as_int(lowered.get("orderid")),
        terminal_no=as_text(lowered.get("terminalno")),
    )


def callback_declined(data: PaymentVerification) -> str | None:
    status = read_callback(data.extra).status
    if status is not None and status != SUCCESS_STATUS:
        return f"parsian callback status {status}"
    return None
