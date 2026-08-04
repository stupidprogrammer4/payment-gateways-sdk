"""Sadad — endpoints and the fixed values its protocol defines."""

from zoneinfo import ZoneInfo

NAME = "sadad"

BASE_URL = "https://sadad.shaparak.ir"
REQUEST_URL = f"{BASE_URL}/VPG/api/v0/Request/PaymentRequest"
VERIFY_URL = f"{BASE_URL}/VPG/api/v0/Advice/Verify"
PURCHASE_URL = f"{BASE_URL}/VPG/Purchase?Token={{token}}"

#: Sadad timestamps are local Tehran time, in US format — its own choice, not a typo.
TEHRAN = ZoneInfo("Asia/Tehran")
TIMESTAMP_FORMAT = "%m/%d/%Y %I:%M:%S %p"

#: Sadad answers ``ResCode`` as either an int or a string depending on the endpoint.
SUCCESS_RES_CODES = (0, "0")

#: 3DES operates on 8-byte blocks, so plaintext is PKCS#7-padded to a multiple of this.
DES3_BLOCK_SIZE = 8
