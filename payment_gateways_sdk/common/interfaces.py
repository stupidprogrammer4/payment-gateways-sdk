from typing import Protocol, runtime_checkable

from payment_gateways_sdk.common.data import (
    CardPaymentRequest,
    InquiryResult,
    PaymentInquiry,
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


@runtime_checkable
class ISyncCardPaymentGateway(Protocol):
    name: str

    def make_card_payment_request(self, data: CardPaymentRequest) -> PaymentResponse: ...

    def verify_payment(self, data: PaymentVerification) -> VerificationResult: ...


@runtime_checkable
class IAsyncCardPaymentGateway(Protocol):
    name: str

    async def make_card_payment_request(self, data: CardPaymentRequest) -> PaymentResponse: ...

    async def verify_payment(self, data: PaymentVerification) -> VerificationResult: ...


@runtime_checkable
class IAsyncPaymentInquiryGateway(Protocol):
    async def inquire_payment(self, data: PaymentInquiry) -> InquiryResult: ...


@runtime_checkable
class ISyncPaymentInquiryGateway(Protocol):
    def inquire_payment(self, data: PaymentInquiry) -> InquiryResult: ...
