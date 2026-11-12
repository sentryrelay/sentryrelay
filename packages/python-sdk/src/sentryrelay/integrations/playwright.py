"""
Sentry Relay Playwright Python Helper (Sync & Async)
"""

import inspect
from typing import Any, Union
from sentryrelay.models import WaitResponse


def fill_otp_code(
    page: Any,
    selector: str,
    target: Union[WaitResponse, str, None],
) -> Any:
    """
    Fills an extracted OTP code into a Playwright page selector.
    Supports both sync `playwright.sync_api.Page` and async `playwright.async_api.Page`.

    Example (Async Playwright):
    ```python
    auth = await relay.wait("bot-1", sender="github.com")
    await fill_otp_code(page, 'input[name="otp"]', auth)
    ```

    Example (Sync Playwright):
    ```python
    auth = relay.wait("bot-1", sender="github.com")
    fill_otp_code(page, 'input[name="otp"]', auth)
    ```
    """
    if target is None:
        raise ValueError("Cannot fill OTP code: code target is None")

    code_str = target.otp_code if isinstance(target, WaitResponse) else target
    if not code_str:
        raise ValueError(
            f"Cannot fill OTP code: WaitResponse did not contain an extracted OTP (matched={getattr(target, 'matched', False)})"
        )

    fill_result = page.fill(selector, str(code_str))
    if inspect.isawaitable(fill_result):
        return fill_result
    return fill_result
