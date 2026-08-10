import asyncio
import json
from typing import Any

import aiohttp
import requests

from payment_gateways_sdk.common.constants import DEFAULT_TIMEOUT
from payment_gateways_sdk.common.exceptions import NetworkError

JSON_HEADERS = {"Content-Type": "application/json"}


def _decode(text: str, status: int, gateway: str) -> dict[str, Any]:
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
