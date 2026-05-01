from opensprite.llms.retry import retry_delay_from_error


class ProviderError(RuntimeError):
    def __init__(self, message, *, status_code=None, headers=None):
        super().__init__(message)
        self.status_code = status_code
        self.headers = headers or {}


def test_retry_delay_parses_retry_after_ms_header():
    delay = retry_delay_from_error(
        ProviderError("rate limited", status_code=429, headers={"retry-after-ms": "250"}),
        now=100.0,
    )

    assert delay.retryable is True
    assert delay.retry_after_ms == 250
    assert delay.next_retry_at == 100.25


def test_retry_delay_parses_retry_after_seconds_header():
    delay = retry_delay_from_error(
        ProviderError("rate limited", status_code=429, headers={"retry-after": "2"}),
        now=100.0,
    )

    assert delay.retryable is True
    assert delay.retry_after_ms == 2000
    assert delay.next_retry_at == 102.0


def test_retry_delay_uses_default_for_5xx_without_header():
    delay = retry_delay_from_error(ProviderError("server error", status_code=503), now=100.0)

    assert delay.retryable is True
    assert delay.retry_after_ms == 1000
    assert delay.next_retry_at == 101.0


def test_retry_delay_parses_textual_rate_limit_delay():
    delay = retry_delay_from_error(ProviderError("please try again in 500ms"), now=100.0)

    assert delay.retryable is True
    assert delay.retry_after_ms == 500
    assert delay.next_retry_at == 100.5


def test_retry_delay_ignores_non_transient_errors():
    delay = retry_delay_from_error(ProviderError("bad request", status_code=400), now=100.0)

    assert delay.retryable is False
    assert delay.retry_after_ms is None
    assert delay.next_retry_at is None
