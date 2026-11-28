"""
Sentry Relay Python SDK Constants
"""

import re
from typing import Final

PRODUCT_NAME: Final[str] = "Sentry Relay"
PRIMARY_DOMAIN: Final[str] = "sentryrelay.com"
DEFAULT_BASE_URL: Final[str] = f"https://{PRIMARY_DOMAIN}"
DEFAULT_INBOUND_EMAIL_DOMAIN: Final[str] = "in.sentryrelay.com"

API_KEY_PREFIX_LIVE: Final[str] = "sr_live_"
API_KEY_PREFIX_TEST: Final[str] = "sr_test_"
API_KEY_RANDOM_LENGTH: Final[int] = 32
API_KEY_REGEX: Final[re.Pattern] = re.compile(r"^sr_(live|test)_[0-9A-Za-z]{32}$")

DEFAULT_MAX_RETRIES: Final[int] = 2
DEFAULT_RETRY_DELAY_SECONDS: Final[float] = 0.15
DEFAULT_TIMEOUT_SECONDS: Final[float] = 60.0

MIN_WAIT_TIMEOUT_SECONDS: Final[int] = 1
DEFAULT_WAIT_TIMEOUT_SECONDS: Final[int] = 30
MAX_WAIT_TIMEOUT_SECONDS: Final[int] = 45
DEFAULT_WAIT_LOOKBACK_MS: Final[int] = 15_000

TOTP_EXPIRING_WINDOW_SECONDS: Final[int] = 5
TOTP_AUTO_WAIT_THRESHOLD_SECONDS: Final[int] = 4
