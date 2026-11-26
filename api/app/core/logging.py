import json
import logging
import re

# Client-supplied ids reach logs verbatim, so bound charset and length.
CORRELATION_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,64}")
DURATION_DECIMALS = 2

request_logger = logging.getLogger("pdc.request")
# Outside tests the root logger sits at WARNING, which would drop these INFO lines.
request_logger.setLevel(logging.INFO)


def is_valid_correlation_id(value: str | None) -> bool:
    return value is not None and CORRELATION_ID_PATTERN.fullmatch(value) is not None


def log_request(
    method: str, path: str, status: int, duration_ms: float, correlation_id: str
) -> None:
    request_logger.info(
        json.dumps(
            {
                "method": method,
                "path": path,
                "status": status,
                "duration_ms": round(duration_ms, DURATION_DECIMALS),
                "correlation_id": correlation_id,
            }
        )
    )
