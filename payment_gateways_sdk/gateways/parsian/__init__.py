"""Parsian / PEC (پارسیان). SOAP over the same clients as the REST gateways."""

from payment_gateways_sdk.gateways.parsian.async_engine import ParsianAsync as ParsianAsync
from payment_gateways_sdk.gateways.parsian.data import (
    ParsianCallbackDetails as ParsianCallbackDetails,
)
from payment_gateways_sdk.gateways.parsian.data import ParsianConfig as ParsianConfig
from payment_gateways_sdk.gateways.parsian.data import (
    ParsianConfirmDetails as ParsianConfirmDetails,
)
from payment_gateways_sdk.gateways.parsian.data import ParsianSaleDetails as ParsianSaleDetails
from payment_gateways_sdk.gateways.parsian.sync_engine import ParsianSync as ParsianSync
