import json


def parse_json_object(raw_text):
    if not raw_text:
        return None
    raw = raw_text.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        parsed = json.loads(raw[start:end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def clamp(value, default=0.5):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    if number < 0:
        return 0.0
    if number > 1:
        return 1.0
    return number


def ensure_list(value):
    return value if isinstance(value, list) else []
