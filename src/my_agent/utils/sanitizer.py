from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEYS = [
    "api_key",
    "apikey"
]

SENSITIVE_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}", #openAI
    r"Bearer\s+[a-zA-Z0-9,_-]+", # Bearer Token
    r"[a-zA-Z0-9]{32,}"
]


REDACTED_PLACEHOLDER = "***REDACTED***"

def sanitize_arguments(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: _sanitize_value(key, value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_arguments(item) for item in data]
    elif isinstance(data, str):
        return _sanitize_string(data)
    else:
        return data
    

def _sanitize_value(key: str, value: Any) -> Any:
    if any(sensitive_key in key.lower() for sensitive_key in SENSITIVE_KEYS):
        if isinstance(value, str):
            return REDACTED_PLACEHOLDER
        elif isinstance(value, (dict, list)):
            return sanitize_arguments(value)
    
    if isinstance(value, (dict, list)):
        return sanitize_arguments(value)
    
    return value

def _sanitize_string(text: str) -> str:
    result = text
    for pattern in SENSITIVE_PATTERNS:
        result = re.sub(pattern, REDACTED_PLACEHOLDER, result)

    return result