"""The two engine interfaces.

Both protocols carry the same two methods with the same arguments and the same return types; the
only difference is the ``async``. Porting a call site from one engine to the other is adding or
removing ``await``, never a rewrite — which is the whole point of shipping both.

These are :class:`typing.Protocol`, so gateways satisfy them structurally. No gateway inherits from
anything here, and your own gateway does not have to either.
"""

from typing import Protocol, runtime_checkable

from payment_gateways_sdk.common.data import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
    VerificationResult,
)


@runtime_checkable
class IAsyncPaymentGateway(Protocol):
    """The async engine: for FastAPI, aiohttp, and anything else on asyncio."""

    name: str

    async def make_payment_request(self, data: PaymentRequest) -> PaymentResponse: ...

    async def verify_payment(self, data: PaymentVerification) -> VerificationResult: ...


@runtime_checkable
class ISyncPaymentGateway(Protocol):
    """The sync engine: for scripts, Django, and Celery workers."""

    name: str

    def make_payment_request(self, data: PaymentRequest) -> PaymentResponse: ...

    def verify_payment(self, data: PaymentVerification) -> VerificationResult: ...
