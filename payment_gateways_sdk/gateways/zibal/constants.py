"""Zibal — endpoints and the fixed values its protocol defines."""

NAME = "zibal"

REQUEST_URL = "https://gateway.zibal.ir/v1/request"
VERIFY_URL = "https://gateway.zibal.ir/v1/verify"
START_URL = "https://gateway.zibal.ir/start/{track_id}"

#: Zibal's public sandbox merchant. Auto-succeeds; cannot route a real rial anywhere.
SANDBOX_MERCHANT = "zibal"

#: The result that means a payment was opened.
REQUEST_SUCCESS_CODE = 100

#: ``100`` verified now, ``201`` already verified — a repeated callback for a payment that arrived.
VERIFY_SUCCESS_CODES = (100, 201)

#: Zibal's own ``status`` values on a verify response, which describe *how* it was paid. They are
#: reported, not acted on: whether money arrived is decided by ``result`` plus the amount check.
PAYMENT_STATUSES = {
    -1: "pending",
    -2: "internal error",
    1: "paid — settled",
    2: "paid — not yet settled",
    3: "cancelled by payer",
    4: "invalid card number",
    5: "insufficient funds",
    6: "wrong PIN",
    7: "too many PIN attempts",
    8: "too many daily transactions",
    9: "daily amount limit exceeded",
    10: "issuer unavailable",
    11: "switch unavailable",
    12: "card inactive",
}
