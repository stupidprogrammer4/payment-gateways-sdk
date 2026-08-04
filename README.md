# payment-gateways-sdk

A unified Python SDK for Iranian payment gateways, with one API surface and two interchangeable engines: **sync** and **async**.

Seven gateways — ZarinPal, Zibal, Yektapay, Top, Sepehr, Sadad and Parsian — behind one pair of interfaces. Every gateway ships `<Name>Sync` and `<Name>Async` with the same two methods, taking and returning the same types. Moving a call site between engines is adding or removing `await`, never a rewrite.

> **Status: early development.** The API below is implemented and tested, but expect breaking changes before `1.0`.

## Why

Every gateway invents its own request shape, its own status codes, and its own idea of what "verify" means. This SDK normalises them, so adding or switching a provider is a one-line change in your application.

- **One API, every gateway** — the same `make_payment_request` / `verify_payment` calls regardless of provider, including the one that speaks SOAP.
- **Two engines, same surface** — identical method names, arguments and return types on both.
- **Fails closed on money** — a gateway that reports a settled amount is checked against the amount *you* recorded, and a mismatch does not settle.
- **Typed end to end** — dataclasses everywhere, `py.typed` shipped, clean under `mypy --strict` and `pyright` in strict mode.
- **Nothing is flattened away** — each gateway also returns its own record with everything *it* reports: fees, masked cards, settlement times, retrieval references.

## Installation

```bash
pip install payment-gateways-sdk
```

Requires Python 3.10 or newer. Two gateways need an extra:

| Extra | Brings | Needed for |
| --- | --- | --- |
| `sadad` | `pycryptodome` | Sadad's 3DES request signing — no stdlib equivalent |
| `parsian` | `zeep[async]` | Parsian, the only SOAP gateway |
| `socks` | `httpx[socks]`, `requests[socks]` | a `socks5://` proxy (plain HTTP proxies need nothing) |
| `all` | all of the above | |

```bash
pip install "payment-gateways-sdk[all]"
```

Sadad's and Parsian's dependencies are imported lazily, so a missing extra raises `DependencyError` naming itself and the command to fix it — rather than an `ImportError` at import time, which would take every *other* gateway down alongside it.

## Quick start

**Amounts are in Rial everywhere.** If your domain keeps Toman, multiply by 10 before calling.

### Sync engine — scripts, Django, Celery workers

```python
from payment_gateways_sdk import PaymentRequest, PaymentVerification, ZibalSync

gateway = ZibalSync(merchant="your-merchant-code")

# 1. Open the payment and send the customer to the gateway.
payment = gateway.make_payment_request(
    PaymentRequest(
        amount=50_000,
        callback_url="https://your-app.example/payments/callback",
        order_id="1001",
        description="Order 1001",
    )
)
save_authority(order, payment.authority)  # store it before redirecting
redirect_to(payment.redirect_url)

# 2. The customer is back. Did the money actually arrive?
result = gateway.verify_payment(
    PaymentVerification(authority=order.authority, amount=50_000, order_id="1001")
)
if result.success:
    mark_paid(order, reference=result.reference)
```

### Async engine — FastAPI, aiohttp, anything on asyncio

The same calls, awaited:

```python
from payment_gateways_sdk import PaymentRequest, PaymentVerification, ZibalAsync

gateway = ZibalAsync(merchant="your-merchant-code")
payment = await gateway.make_payment_request(
    PaymentRequest(amount=50_000, callback_url="...", order_id="1001")
)
result = await gateway.verify_payment(
    PaymentVerification(authority=payment.authority, amount=50_000, order_id="1001")
)
```

Concurrency is real — these overlap rather than queueing:

```python
payments = await asyncio.gather(*(gateway.make_payment_request(r) for r in requests))
```

Run [`main.py`](main.py) to see all of this working against Zibal's public sandbox, which needs no credentials and moves no money.

## Supported gateways

| Gateway | Class prefix | Credentials | Extra | Numeric `order_id` | Verifies amount |
| --- | --- | --- | :---: | :---: | :---: |
| ZarinPal (زرین‌پال) | `Zarinpal` | `merchant_id`, `sandbox=False` | — | no | by ZarinPal |
| Zibal (زیبال) | `Zibal` | `merchant` (defaults to sandbox) | — | no | yes |
| Yektapay (یکتاپی) | `Yektapay` | `token` | — | no | yes |
| Top / PNA (تاپ) | `Top` | `username`, `password` | — | **yes** | not reported |
| Sepehr (سپهر) | `Sepehr` | `terminal_id` | — | **yes** | yes |
| Sadad (سداد) | `Sadad` | `merchant_id`, `terminal_id`, `terminal_key` | `sadad` | **yes** | yes |
| Parsian (پارسیان) | `Parsian` | `pin`, `proxy=""` | `parsian` | **yes** | not reported |

Every gateway also takes `timeout=15.0`, except Parsian.

**Numeric `order_id`** — Top, Sepehr, Sadad and Parsian declare that field as a 64-bit integer. Top rejects a UUID in its ASP.NET layer *before* its own code runs, with no status and no message in the body, so the SDK raises `ConfigurationError` locally instead of letting the payer see "unknown error".

**Verifies amount** — where the gateway reports a settled amount, it is compared to the amount the payment was opened for and a mismatch fails. Where it reports none, what binds the answer to the payment is that the call is scoped to a token the SDK issued. ZarinPal checks the amount at its end: it is part of the verify *request*, so a transaction settled for anything else comes back as an error rather than as success.

**Parsian** talks SOAP through `zeep`, which reads a WSDL before its first call. That is cached per process, so it costs the first payment and nothing after — call `ParsianAsync(pin=...).warm_up()` during application startup to pay it before any customer is waiting.

## Credentials

Constructor arguments, always. The SDK never reads them from the environment.

```python
ZarinpalSync(merchant_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
ZarinpalSync(merchant_id="...", sandbox=True)
ZibalSync(merchant="your-merchant-code")
YektapaySync(token="your-api-token")
TopSync(username="your-username", password="your-password")
SepehrSync(terminal_id="your-terminal-id")
SadadSync(merchant_id="...", terminal_id="...", terminal_key="base64-3des-key")
ParsianSync(pin="your-login-account", proxy="socks5://127.0.0.1:1080")
```

Build one gateway per merchant rather than caching one globally — an instance carries exactly one merchant's credentials, so a shared one sends everybody's money to whoever was configured first.

To pick a gateway from a database row instead of from your source:

```python
from payment_gateways_sdk import available, get_async_gateway, get_sync_gateway

available()  # ('parsian', 'sadad', ..., 'zibal')
gateway = get_sync_gateway("zarinpal", merchant_id="...")
gateway = get_async_gateway("zibal", merchant="...")
```

## Callbacks

Most gateways verify against the token they issued, so the callback is only a signal to go and ask. Two need more, and take it through `PaymentVerification.extra` — pass the callback's payload straight through, and the SDK reads what it needs:

```python
# Sepehr verifies against `digitalreceipt` from the bank's POST, not the token it issued.
# request.form is e.g. {"digitalreceipt": "...", "invoiceid": "1001", "rrn": "..."}
SepehrSync(terminal_id="...").verify_payment(
    PaymentVerification(authority=stored_token, amount=50_000, order_id="1001", extra=request.form)
)

# Parsian reads `status` and `RRN`. A non-zero status means the payer cancelled, and the SDK
# refuses to confirm rather than asking the bank to settle something that never happened.
# request.form is e.g. {"Token": "...", "status": "0", "RRN": "..."}
ParsianSync(pin="...").verify_payment(
    PaymentVerification(authority=stored_token, amount=50_000, order_id="1001", extra=request.form)
)
```

Field names are matched case-insensitively, because both banks send names in a different case than they document.

The `authority` must come from **your** database, never from the callback's query string. That is what binds the answer to the payment you actually opened.

## Gateway-specific data

`result.details` is that gateway's own record, typed — no digging through `raw`:

```python
result = gateway.verify_payment(...)

result.reference  # settlement reference, on every gateway
result.amount  # settled amount in Rial
result.details  # e.g. ZibalVerifyDetails(...)

result.details.paid_at  # Zibal: when it settled
result.details.card_number  # Zibal: masked PAN
result.details.wage  # Zibal: the commission it took
result.details.status_text  # Zibal: its status code, decoded
```

| Gateway | Records |
| --- | --- |
| ZarinPal | `ZarinpalRequestDetails` · `ZarinpalVerifyDetails` — fee, fee type, `card_pan`, `card_hash` |
| Zibal | `ZibalRequestDetails` · `ZibalVerifyDetails` — `paid_at`, `card_number`, `wage`, decoded status |
| Yektapay | `YektapayOrderDetails` · `YektapayVerifyDetails` |
| Top | `TopRequestDetails` · `TopVerifyDetails` — `service_url`, `rrn` |
| Sepehr | `SepehrTokenDetails` · `SepehrCallbackDetails` · `SepehrAdviceDetails` |
| Sadad | `SadadRequestDetails` · `SadadVerifyDetails` — `retrival_ref_no`, `system_trace_no` |
| Parsian | `ParsianSaleDetails` · `ParsianConfirmDetails` · `ParsianCallbackDetails` — `card_number_masked`, `rrn` |

## Errors

**Opening a payment raises. Verifying one does not.**

That asymmetry is deliberate. A failure while opening means no payment exists at the gateway, so failing loudly stops you redirecting a customer into nothing. A failure while verifying may concern money that already moved, so it comes back as a result you can retry from and reconcile — never as an exception in front of a returning payer.

```python
from payment_gateways_sdk import (
    ConfigurationError,  # bad or missing credentials, non-numeric order_id
    DependencyError,  # a gateway's extra is not installed
    GatewayError,  # the gateway was reached and declined  (.code, .raw)
    NetworkError,  # timeout, connection refused, undecodable response
    PaymentError,  # base for everything above
)

try:
    payment = gateway.make_payment_request(request)
except GatewayError as exc:
    log.warning("declined: %s (code=%s) raw=%s", exc, exc.code, exc.raw)
except PaymentError:
    raise

result = gateway.verify_payment(verification)
if not result:  # VerificationResult is falsy when unpaid
    log.warning("not paid: %s", result.message)
```

## License

MIT — see [LICENSE](LICENSE).
