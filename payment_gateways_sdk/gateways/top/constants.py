"""Top / PNA — endpoints and the fixed values its protocol defines."""

from zoneinfo import ZoneInfo

NAME = "top"

BASE_URL = "https://pay.top.ir/api/WPG"
REQUEST_URL = f"{BASE_URL}/CreateOrder"
VERIFY_URL = f"{BASE_URL}/ConfirmPurchase"

#: Top timestamps are local Tehran time, not UTC.
TEHRAN = ZoneInfo("Asia/Tehran")
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"

#: Top's "no error" status. Anything else is a decline, whatever the HTTP code said.
SUCCESS_STATUS = 0
