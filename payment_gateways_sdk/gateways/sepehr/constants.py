"""Sepehr / Mabna — endpoints and the fixed values its protocol defines."""

NAME = "sepehr"

TOKEN_URL = "https://sepehr.shaparak.ir/Rest/V1/PeymentApi/GetToken"  # noqa: S105 — a URL
PAY_URL = "https://sepehr.shaparak.ir/Payment/Pay"
ADVICE_URL = "https://sepehr.shaparak.ir/Rest/V1/PeymentApi/Advice"

#: The callback field carrying the receipt Advice needs. Read from ``PaymentVerification.extra``.
RECEIPT_KEY = "digitalreceipt"

#: The status that means a token was issued.
TOKEN_SUCCESS_STATUS = 0

#: ``ok`` settled now, ``duplicate`` already settled — a second Advice for the same receipt.
ADVICE_SUCCESS_STATUSES = ("ok", "duplicate")
