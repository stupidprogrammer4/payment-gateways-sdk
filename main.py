"""How to use payment-gateways-sdk.

Run it — ``python main.py`` — and it will open and verify a real payment against Zibal's public
sandbox, which needs no credentials and moves no money. Everything else here is example code you
can copy; the gateway-specific functions need that gateway's own credentials to run.

The whole SDK is two calls:

    payment = gateway.make_payment_request(PaymentRequest(...))   # send the customer to
                                                                  # payment.redirect_url
    result  = gateway.verify_payment(PaymentVerification(...))    # after they come back

Every gateway ships two classes with those same two methods — ``<Name>Sync`` and ``<Name>Async``.
Moving between engines is adding or removing ``await``, never a rewrite.

**Amounts are in Rial everywhere.** If your domain keeps Toman, multiply by 10 before calling.
"""

import asyncio

from payment_gateways_sdk import (
    ConfigurationError,
    DependencyError,
    GatewayError,
    NetworkError,
    ParsianAsync,
    ParsianSync,
    PaymentError,
    PaymentRequest,
    PaymentVerification,
    SadadSync,
    SepehrSync,
    TopSync,
    VerificationResult,
    YektapaySync,
    ZarinpalAsync,
    ZarinpalSync,
    ZibalAsync,
    ZibalSync,
    available,
    get_async_gateway,
    get_sync_gateway,
)
from payment_gateways_sdk.gateways.zibal import ZibalVerifyDetails

CALLBACK_URL = "https://your-app.example/payments/callback"


# ---------------------------------------------------------------------------------------------
# 1. The sync engine — scripts, Django, Celery workers
# ---------------------------------------------------------------------------------------------


def open_a_payment_sync(merchant: str, order_id: str, amount_rial: int) -> tuple[str, str]:
    """Step one: open a payment and get the URL to send the customer to.

    Store the returned ``authority`` against your order before redirecting. It is the only thing
    that lets you verify the payment afterwards, and it must come from *your* database on the way
    back — never from the callback's query string.
    """
    gateway = ZibalSync(merchant=merchant)
    payment = gateway.make_payment_request(
        PaymentRequest(
            amount=amount_rial,
            callback_url=CALLBACK_URL,
            order_id=order_id,
            description=f"Order {order_id}",
            mobile="09120000000",
        )
    )
    return payment.authority, payment.redirect_url


def verify_a_payment_sync(merchant: str, authority: str, amount_rial: int) -> VerificationResult:
    """Step two: the customer is back — did the money actually arrive?

    ``amount`` is the amount *you* recorded when opening the payment, not anything the callback
    said. Gateways that report a settled amount are checked against it, and a mismatch fails.

    This never raises for a declined payment: someone standing in front of a bank redirect must not
    meet a stack trace. Check ``result.success``.
    """
    gateway = ZibalSync(merchant=merchant)
    return gateway.verify_payment(
        PaymentVerification(authority=authority, amount=amount_rial, order_id="1001")
    )


# ---------------------------------------------------------------------------------------------
# 2. The async engine — FastAPI, aiohttp, anything on asyncio
# ---------------------------------------------------------------------------------------------


async def open_a_payment_async(merchant: str, order_id: str, amount_rial: int) -> tuple[str, str]:
    """The same two calls, awaited. Note the identical arguments and return types."""
    gateway = ZibalAsync(merchant=merchant)
    payment = await gateway.make_payment_request(
        PaymentRequest(amount=amount_rial, callback_url=CALLBACK_URL, order_id=order_id)
    )
    return payment.authority, payment.redirect_url


async def open_many_at_once(merchant: str, count: int) -> list[str]:
    """Why the async engine exists: these go out concurrently, not one after another."""
    gateway = ZibalAsync(merchant=merchant)
    requests = [
        gateway.make_payment_request(
            PaymentRequest(amount=10_000, callback_url=CALLBACK_URL, order_id=str(1000 + i))
        )
        for i in range(count)
    ]
    payments = await asyncio.gather(*requests)
    return [payment.redirect_url for payment in payments]


# ---------------------------------------------------------------------------------------------
# 3. Every gateway, and what each one needs
# ---------------------------------------------------------------------------------------------


def build_every_gateway() -> None:
    """Credentials are constructor arguments — the SDK never reads them from the environment.

    Keep them in your own settings layer or secret manager and pass them in. Build one gateway per
    merchant rather than caching one globally: an instance carries exactly one merchant's
    credentials, so a shared one sends everybody's money to whoever was configured first.
    """
    ZarinpalSync(merchant_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
    ZarinpalAsync(merchant_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", sandbox=True)
    ZibalSync(merchant="your-merchant-code")  # defaults to the "zibal" sandbox merchant
    YektapaySync(token="your-api-token")  # noqa: S106 — a placeholder, not a secret
    TopSync(username="your-username", password="your-password")  # noqa: S106
    SepehrSync(terminal_id="your-terminal-id")
    SadadSync(  # needs the extra: pip install "payment-gateways-sdk[sadad]"
        merchant_id="your-merchant-id",
        terminal_id="your-terminal-id",
        terminal_key="base64-3des-key",
    )
    ParsianSync(pin="your-login-account")  # needs: pip install "…[parsian]" (zeep)
    ParsianAsync(pin="your-login-account", proxy="socks5://127.0.0.1:1080")  # optional route


def pick_a_gateway_at_runtime(name: str) -> None:
    """When the gateway comes from a database row rather than from your source code."""
    print("available gateways:", available())
    sync_gateway = get_sync_gateway(name, merchant="zibal")
    async_gateway = get_async_gateway(name, merchant="zibal")
    print(f"built {sync_gateway.name} for both engines:", sync_gateway, async_gateway)


# ---------------------------------------------------------------------------------------------
# 4. Gateways whose verification needs the callback payload
# ---------------------------------------------------------------------------------------------


def verify_sepehr(terminal_id: str, callback_form: dict[str, str]) -> VerificationResult:
    """Sepehr verifies against ``digitalreceipt`` from the bank's callback, not the token it issued.

    Pass the callback's POST body straight through in ``extra``; the SDK reads what it needs and
    ignores the rest. Field names are matched case-insensitively, because the bank sends
    ``digitalreceipt`` lower-cased while documenting it camel-cased.

    This is still safe: the receipt only *selects* which transaction to ask about. Whether the money
    arrived is answered by Sepehr's own API and checked against the amount you recorded.
    """
    return SepehrSync(terminal_id=terminal_id).verify_payment(
        PaymentVerification(
            authority="the-token-you-stored",
            amount=50_000,
            order_id="1001",
            extra=callback_form,  # {"digitalreceipt": "...", "invoiceid": "1001", ...}
        )
    )


def verify_parsian(pin: str, callback_form: dict[str, str]) -> VerificationResult:
    """Parsian reads ``status`` and ``RRN`` from its callback.

    A non-zero ``status`` means the payer cancelled or timed out, and the SDK refuses to confirm
    rather than asking the bank to settle a transaction that never happened.
    """
    return ParsianSync(pin=pin).verify_payment(
        PaymentVerification(
            authority="the-token-you-stored",
            amount=50_000,
            order_id="1001",
            extra=callback_form,  # {"Token": "...", "status": "0", "RRN": "..."}
        )
    )


# ---------------------------------------------------------------------------------------------
# 5. Errors
# ---------------------------------------------------------------------------------------------


def handle_errors(merchant: str) -> None:
    """Opening a payment raises; verifying it does not.

    That asymmetry is deliberate. A failure while opening means no payment exists at the gateway,
    so failing loudly stops you redirecting a customer into nothing. A failure while verifying may
    concern money that already moved, so it comes back as a result you can retry from and
    reconcile — never as an exception in front of a returning payer.
    """
    try:
        ZibalSync(merchant=merchant).make_payment_request(
            PaymentRequest(amount=1_000, callback_url=CALLBACK_URL, order_id="1001")
        )
    except ConfigurationError as exc:
        print("misconfigured — fix this before taking money:", exc)
    except GatewayError as exc:
        print(f"the gateway declined (code={exc.code}):", exc)
        print("its untouched response:", exc.raw)
    except NetworkError as exc:
        print("could not reach the gateway:", exc)
    except DependencyError as exc:
        print("a gateway extra is not installed:", exc)
    except PaymentError as exc:  # the base class — catches all of the above
        print("payment failed:", exc)

    result = ZibalSync(merchant=merchant).verify_payment(
        PaymentVerification(authority="404040", amount=1_000)
    )
    if not result:  # VerificationResult is falsy when the money did not arrive
        print("not paid:", result.message)


# ---------------------------------------------------------------------------------------------
# 6. Gateway-specific data
# ---------------------------------------------------------------------------------------------


def read_gateway_specific_details(result: VerificationResult) -> None:
    """``result.details`` is that gateway's own record, typed — no digging through ``raw``.

    Zibal reports the settlement time, the masked card and its commission; ZarinPal reports a fee
    breakdown and a card hash; Parsian reports the masked card and the Shaparak RRN. Each gateway's
    record carries what that gateway actually sends, so nothing is flattened away.
    """
    print("reference:", result.reference)  # on every gateway
    print("amount   :", result.amount)
    print("details  :", result.details)  # e.g. ZibalVerifyDetails(...)

    if isinstance(result.details, ZibalVerifyDetails):
        print("paid at    :", result.details.paid_at)
        print("card       :", result.details.card_number)
        print("zibal wage :", result.details.wage)
        print("status     :", result.details.status, result.details.status_text)


# ---------------------------------------------------------------------------------------------
# A runnable demo, against Zibal's public sandbox
# ---------------------------------------------------------------------------------------------

SANDBOX_MERCHANT = "zibal"
"""Zibal's public sandbox merchant. Auto-succeeds and cannot route a real rial anywhere."""


def demo_sync() -> None:
    print("\n--- sync engine, Zibal sandbox ---")
    authority, redirect_url = open_a_payment_sync(SANDBOX_MERCHANT, "1001", 50_000)
    print("authority   :", authority)
    print("send user to:", redirect_url)

    # This verification is expected to fail, and that is the correct answer: nobody has opened the
    # redirect URL above and paid, so no money arrived. Zibal says "transaction failed" and the SDK
    # reports it rather than settling. Open the URL in a browser and pay on the sandbox card form,
    # then run the verify again to see a success.
    result = verify_a_payment_sync(SANDBOX_MERCHANT, authority, 50_000)
    print("verified    :", result.success, "(expected — the payment page was never completed)")
    print("message     :", result.message)
    if result.success:
        read_gateway_specific_details(result)


async def demo_async() -> None:
    print("\n--- async engine, Zibal sandbox ---")
    authority, redirect_url = await open_a_payment_async(SANDBOX_MERCHANT, "1002", 50_000)
    print("authority   :", authority)
    print("send user to:", redirect_url)

    print("\n--- three payments opened concurrently ---")
    for url in await open_many_at_once(SANDBOX_MERCHANT, 3):
        print("  ", url)


def demo_registry() -> None:
    print("\n--- the registry ---")
    pick_a_gateway_at_runtime("zibal")


def main() -> None:
    print("payment-gateways-sdk demo")
    print("gateways:", ", ".join(available()))
    demo_registry()
    try:
        demo_sync()
        asyncio.run(demo_async())
    except NetworkError as exc:
        # The sandbox is a real host, so this demo needs an internet connection.
        print("\ncould not reach the Zibal sandbox — are you offline?")
        print("  ", exc)
    print("\nAmounts above are in Rial. See the functions in this file for every other gateway.")


if __name__ == "__main__":
    main()
