"""A unified SDK for Iranian payment gateways, in a sync and an async flavour.

Seven gateways — ZarinPal, Zibal, Yektapay, Top, Sepehr, Sadad and Parsian — behind one pair of
interfaces. Every gateway ships ``<Name>Sync`` and ``<Name>Async`` with the same two methods,
:meth:`make_payment_request` and :meth:`verify_payment`, taking and returning the same types.

Amounts are in **Rial** everywhere.

    from payment_gateways_sdk import PaymentRequest, ZarinpalSync

    gateway = ZarinpalSync(merchant_id="…")
    payment = gateway.make_payment_request(
        PaymentRequest(amount=50_000, callback_url="https://example.com/cb", order_id="1001")
    )
    print(payment.redirect_url)

Each gateway package is laid out the same way: ``constants.py`` (endpoints and the fixed values its
protocol defines), ``data.py`` (credentials and the gateway's own result records — dataclasses
only), ``helpers.py`` (the pure functions that build payloads and read responses), and
``sync_engine.py`` / ``async_engine.py``.
"""

from payment_gateways_sdk.common.data import GatewayDetails as GatewayDetails
from payment_gateways_sdk.common.data import PaymentRequest as PaymentRequest
from payment_gateways_sdk.common.data import PaymentResponse as PaymentResponse
from payment_gateways_sdk.common.data import PaymentVerification as PaymentVerification
from payment_gateways_sdk.common.data import VerificationResult as VerificationResult
from payment_gateways_sdk.common.exceptions import ConfigurationError as ConfigurationError
from payment_gateways_sdk.common.exceptions import DependencyError as DependencyError
from payment_gateways_sdk.common.exceptions import GatewayError as GatewayError
from payment_gateways_sdk.common.exceptions import NetworkError as NetworkError
from payment_gateways_sdk.common.exceptions import PaymentError as PaymentError
from payment_gateways_sdk.common.interfaces import IAsyncPaymentGateway as IAsyncPaymentGateway
from payment_gateways_sdk.common.interfaces import ISyncPaymentGateway as ISyncPaymentGateway
from payment_gateways_sdk.gateways import ParsianAsync as ParsianAsync
from payment_gateways_sdk.gateways import ParsianSync as ParsianSync
from payment_gateways_sdk.gateways import SadadAsync as SadadAsync
from payment_gateways_sdk.gateways import SadadSync as SadadSync
from payment_gateways_sdk.gateways import SepehrAsync as SepehrAsync
from payment_gateways_sdk.gateways import SepehrSync as SepehrSync
from payment_gateways_sdk.gateways import TopAsync as TopAsync
from payment_gateways_sdk.gateways import TopSync as TopSync
from payment_gateways_sdk.gateways import YektapayAsync as YektapayAsync
from payment_gateways_sdk.gateways import YektapaySync as YektapaySync
from payment_gateways_sdk.gateways import ZarinpalAsync as ZarinpalAsync
from payment_gateways_sdk.gateways import ZarinpalSync as ZarinpalSync
from payment_gateways_sdk.gateways import ZibalAsync as ZibalAsync
from payment_gateways_sdk.gateways import ZibalSync as ZibalSync
from payment_gateways_sdk.gateways import available as available
from payment_gateways_sdk.gateways import get_async_gateway as get_async_gateway
from payment_gateways_sdk.gateways import get_sync_gateway as get_sync_gateway

__version__ = "0.1.0"
