from __future__ import annotations


class SafiaError(Exception):
    """Error returned to clients as {"error": {"code", "message", "retryable"}}."""

    def __init__(self, code: str, message: str, status: int, retryable: bool = False,
                 details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.retryable = retryable
        self.details = details or {}


def llm_unavailable(msg: str = "The language model is not reachable right now.") -> SafiaError:
    return SafiaError("LLM_UNAVAILABLE", msg, 502, retryable=True)


def llm_timeout() -> SafiaError:
    return SafiaError("LLM_TIMEOUT", "The language model took too long to answer.", 504, retryable=True)


def rate_limited() -> SafiaError:
    return SafiaError("RATE_LIMITED", "Too many requests to the language model. Try again shortly.", 429, retryable=True)


def llm_auth() -> SafiaError:
    return SafiaError("LLM_AUTH", "The backend's LLM credentials were rejected. Check UTH_KEY.", 502)


def turn_not_found() -> SafiaError:
    return SafiaError("TURN_NOT_FOUND", "Unknown or already completed turn_id.", 404)


def turn_expired() -> SafiaError:
    return SafiaError("TURN_EXPIRED", "This turn expired. Send the message again.", 410, retryable=True)


def invalid_tool_result(msg: str, details: dict | None = None) -> SafiaError:
    return SafiaError("INVALID_TOOL_RESULT", msg, 422, details=details)
