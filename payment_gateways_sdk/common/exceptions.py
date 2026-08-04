"""One error hierarchy across every gateway.

Errors are raised on the **request** path, where failing loudly means a customer is never sent to a
gateway that has no payment waiting for them. The **verify** path returns
:class:`~payment_gateways_sdk.common.data.VerificationResult` with ``success=False`` instead —
raising there would turn a payment that may well have been paid into a crash for someone standing
in front of their bank's redirect.
"""

from typing import Any


class PaymentError(Exception):
    """Base for everything this SDK raises."""


class ConfigurationError(PaymentError):
    """The gateway cannot be addressed as configured.

    Raised at construction, or as soon as a required field is found unusable — before any network
    call, so a half-configured gateway fails while you are wiring it up rather than mid-payment.
    """


class NetworkError(PaymentError):
    """The gateway could not be reached, timed out, or answered with something undecodable."""


class GatewayError(PaymentError):
    """The gateway was reached and declined."""

    def __init__(
        self,
        message: str,
        *,
        code: Any = None,
        raw: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        """The gateway's own status/result code, as it sent it."""
        self.raw = raw or {}
        """The gateway's decoded response, untouched."""


class DependencyError(PaymentError):
    """The gateway needs an optional dependency that is not installed.

    Sadad needs 3DES from ``pycryptodome``, which has no stdlib equivalent and is not a base
    dependency. It is imported lazily so that its absence takes out only Sadad — an ImportError at
    module scope would break every other gateway alongside it.
    """
