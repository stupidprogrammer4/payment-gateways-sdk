"""Every gateway, plus a registry for picking one by name at runtime.

Each gateway directory holds the same five things: ``constants.py`` (endpoints and the fixed values
its protocol defines), ``data.py`` (credentials and the gateway's own result records — dataclasses
only), ``helpers.py`` (the pure functions that build payloads and read responses), and
``sync_engine.py`` / ``async_engine.py``, which are thin shells over both. That split is why the
two engines cannot drift apart: every decision about what a gateway said lives in ``helpers.py``
and is shared, so only the transport call differs.

The registry holds **classes, not instances**. A shared instance can carry exactly one merchant's
credentials, so build one per merchant with :func:`get_sync_gateway` / :func:`get_async_gateway`
rather than caching a gateway globally.
"""

from typing import Any

from payment_gateways_sdk.common.exceptions import ConfigurationError
from payment_gateways_sdk.common.interfaces import IAsyncPaymentGateway, ISyncPaymentGateway
from payment_gateways_sdk.gateways.parsian import ParsianAsync as ParsianAsync
from payment_gateways_sdk.gateways.parsian import ParsianCallbackDetails as ParsianCallbackDetails
from payment_gateways_sdk.gateways.parsian import ParsianConfig as ParsianConfig
from payment_gateways_sdk.gateways.parsian import ParsianConfirmDetails as ParsianConfirmDetails
from payment_gateways_sdk.gateways.parsian import ParsianSaleDetails as ParsianSaleDetails
from payment_gateways_sdk.gateways.parsian import ParsianSync as ParsianSync
from payment_gateways_sdk.gateways.sadad import SadadAsync as SadadAsync
from payment_gateways_sdk.gateways.sadad import SadadConfig as SadadConfig
from payment_gateways_sdk.gateways.sadad import SadadRequestDetails as SadadRequestDetails
from payment_gateways_sdk.gateways.sadad import SadadSync as SadadSync
from payment_gateways_sdk.gateways.sadad import SadadVerifyDetails as SadadVerifyDetails
from payment_gateways_sdk.gateways.sepehr import SepehrAdviceDetails as SepehrAdviceDetails
from payment_gateways_sdk.gateways.sepehr import SepehrAsync as SepehrAsync
from payment_gateways_sdk.gateways.sepehr import SepehrCallbackDetails as SepehrCallbackDetails
from payment_gateways_sdk.gateways.sepehr import SepehrConfig as SepehrConfig
from payment_gateways_sdk.gateways.sepehr import SepehrSync as SepehrSync
from payment_gateways_sdk.gateways.sepehr import SepehrTokenDetails as SepehrTokenDetails
from payment_gateways_sdk.gateways.top import TopAsync as TopAsync
from payment_gateways_sdk.gateways.top import TopConfig as TopConfig
from payment_gateways_sdk.gateways.top import TopRequestDetails as TopRequestDetails
from payment_gateways_sdk.gateways.top import TopSync as TopSync
from payment_gateways_sdk.gateways.top import TopVerifyDetails as TopVerifyDetails
from payment_gateways_sdk.gateways.yektapay import YektapayAsync as YektapayAsync
from payment_gateways_sdk.gateways.yektapay import YektapayConfig as YektapayConfig
from payment_gateways_sdk.gateways.yektapay import YektapayOrderDetails as YektapayOrderDetails
from payment_gateways_sdk.gateways.yektapay import YektapaySync as YektapaySync
from payment_gateways_sdk.gateways.yektapay import YektapayVerifyDetails as YektapayVerifyDetails
from payment_gateways_sdk.gateways.zarinpal import ZarinpalAsync as ZarinpalAsync
from payment_gateways_sdk.gateways.zarinpal import ZarinpalConfig as ZarinpalConfig
from payment_gateways_sdk.gateways.zarinpal import ZarinpalRequestDetails as ZarinpalRequestDetails
from payment_gateways_sdk.gateways.zarinpal import ZarinpalSync as ZarinpalSync
from payment_gateways_sdk.gateways.zarinpal import ZarinpalVerifyDetails as ZarinpalVerifyDetails
from payment_gateways_sdk.gateways.zibal import ZibalAsync as ZibalAsync
from payment_gateways_sdk.gateways.zibal import ZibalConfig as ZibalConfig
from payment_gateways_sdk.gateways.zibal import ZibalRequestDetails as ZibalRequestDetails
from payment_gateways_sdk.gateways.zibal import ZibalSync as ZibalSync
from payment_gateways_sdk.gateways.zibal import ZibalVerifyDetails as ZibalVerifyDetails

SYNC_GATEWAYS: dict[str, type[ISyncPaymentGateway]] = {
    "parsian": ParsianSync,
    "sadad": SadadSync,
    "sepehr": SepehrSync,
    "top": TopSync,
    "yektapay": YektapaySync,
    "zarinpal": ZarinpalSync,
    "zibal": ZibalSync,
}

ASYNC_GATEWAYS: dict[str, type[IAsyncPaymentGateway]] = {
    "parsian": ParsianAsync,
    "sadad": SadadAsync,
    "sepehr": SepehrAsync,
    "top": TopAsync,
    "yektapay": YektapayAsync,
    "zarinpal": ZarinpalAsync,
    "zibal": ZibalAsync,
}


def available() -> tuple[str, ...]:
    """Every gateway name, sorted. The same names work in both engines."""
    return tuple(sorted(SYNC_GATEWAYS))


def get_sync_gateway(name: str, **credentials: Any) -> ISyncPaymentGateway:
    """Build a sync gateway by name, e.g. ``get_sync_gateway("zarinpal", merchant_id="…")``."""
    try:
        gateway_cls = SYNC_GATEWAYS[name]
    except KeyError:
        raise ConfigurationError(
            f"unknown gateway {name!r} — available: {', '.join(available())}"
        ) from None
    return gateway_cls(**credentials)


def get_async_gateway(name: str, **credentials: Any) -> IAsyncPaymentGateway:
    """Build an async gateway by name, e.g. ``get_async_gateway("zibal", merchant="…")``."""
    try:
        gateway_cls = ASYNC_GATEWAYS[name]
    except KeyError:
        raise ConfigurationError(
            f"unknown gateway {name!r} — available: {', '.join(available())}"
        ) from None
    return gateway_cls(**credentials)
