"""ZarinPal — endpoints and the fixed values its protocol defines."""

NAME = "zarinpal"

REQUEST_URL = "https://payment.zarinpal.com/pg/v4/payment/request.json"
VERIFY_URL = "https://payment.zarinpal.com/pg/v4/payment/verify.json"
START_URL = "https://payment.zarinpal.com/pg/StartPay/{authority}"

SANDBOX_REQUEST_URL = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
SANDBOX_VERIFY_URL = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
SANDBOX_START_URL = "https://sandbox.zarinpal.com/pg/StartPay/{authority}"

#: ZarinPal rejects a request with no description.
DEFAULT_DESCRIPTION = "پرداخت سفارش"

#: The code that means a payment was opened.
REQUEST_SUCCESS_CODE = 100

#: ``100`` verified now, ``101`` already verified — a repeated callback for a payment that arrived.
VERIFY_SUCCESS_CODES = (100, 101)
