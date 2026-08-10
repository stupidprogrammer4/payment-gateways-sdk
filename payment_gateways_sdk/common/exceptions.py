from typing import Any


class PaymentError(Exception):
    """Base for everything this SDK raises."""


class ConfigurationError(PaymentError):
    pass


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
    pass
