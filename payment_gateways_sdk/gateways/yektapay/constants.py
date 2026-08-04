"""Yektapay — endpoints and the fixed values its protocol defines."""

NAME = "yektapay"

REQUEST_URL = "https://api.yektapay.app/api/v1/merchant/orders/"
VERIFY_URL = "https://api.yektapay.app/api/v1/merchant/orders/{authority}/verify/"
START_URL = "https://panel.yektapay.app/gateway/{authority}"

DEFAULT_TITLE = "پرداخت سفارش"

#: The only ``status`` Yektapay reports for money that actually arrived.
SUCCESS_STATUS = "successful"
