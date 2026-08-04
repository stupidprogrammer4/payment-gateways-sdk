"""One JSON round-trip, in both flavours, shared by every REST gateway.

Six of the seven gateways speak REST/JSON and differ only in URL, payload and headers, so the
transport lives here once. Keeping it in one place is also what stops the async engine from
quietly growing a blocking call: a synchronous request inside a coroutine parks the entire event
loop for up to the timeout, so one slow gateway stalls every other request in the process, not just
the payer's.

**Two clients, on purpose.** ``aiohttp`` drives the async engine and has no synchronous API, so the
sync engine uses ``requests``. Both are normalised here — same arguments, same return type, same
errors — so nothing above this module can tell which one ran.

Both functions raise :class:`NetworkError` for anything that stopped the round-trip from
completing. Callers on the verify path catch it and return a failed
:class:`~payment_gateways_sdk.common.data.VerificationResult` instead.
"""

import asyncio
import json
from typing import Any

import aiohttp
import requests

from payment_gateways_sdk.common.constants import DEFAULT_TIMEOUT
from payment_gateways_sdk.common.exceptions import NetworkError

JSON_HEADERS = {"Content-Type": "application/json"}


def _decode(text: str, status: int, gateway: str) -> dict[str, Any]:
    """Decode a gateway response into a dict, or say precisely what arrived instead.

    The body is parsed from text rather than through the client's own JSON helper, because several
    of these gateways answer JSON while declaring ``text/html`` or no content type at all —
    ``aiohttp`` refuses those by default, and a payment is not the place to discover it.

    The HTTP status deliberately decides nothing on its own: gateways here report business
    failures — declined, bad terminal, duplicate — in the *body* of a 200. Each gateway reads its
    own status field. A 4xx/5xx usually means the request never reached the gateway's own code, and
    shows up as a body that will not parse.
    """
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise NetworkError(
            f"{gateway} answered HTTP {status} with non-JSON content: {text[:200]!r}"
        ) from exc
    if not isinstance(data, dict):
        raise NetworkError(f"{gateway} answered with {type(data).__name__}, not an object")
    return data


def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    gateway: str,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """POST JSON and return the decoded object. Sync engine, over ``requests``."""
    try:
        response = requests.post(
            url, json=payload, headers={**JSON_HEADERS, **(headers or {})}, timeout=timeout
        )
    except requests.Timeout as exc:
        raise NetworkError(f"{gateway} did not answer within {timeout}s") from exc
    except requests.RequestException as exc:
        raise NetworkError(f"{gateway} request failed: {exc}") from exc
    return _decode(response.text, response.status_code, gateway)


async def apost_json(
    url: str,
    payload: dict[str, Any],
    *,
    gateway: str,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """POST JSON and return the decoded object. Async engine, over ``aiohttp``."""
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    try:
        async with (
            aiohttp.ClientSession(timeout=client_timeout) as session,
            session.post(
                url, json=payload, headers={**JSON_HEADERS, **(headers or {})}
            ) as response,
        ):
            text = await response.text()
            status = response.status
    except asyncio.TimeoutError as exc:
        raise NetworkError(f"{gateway} did not answer within {timeout}s") from exc
    except aiohttp.ClientError as exc:
        raise NetworkError(f"{gateway} request failed: {exc}") from exc
    return _decode(text, status, gateway)
