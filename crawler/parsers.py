import json
import re


def parse_recommend_reason_list(raw):
    """Parse recommend_reason_list from ranking API to extract hot_score and hot_content."""
    result = {"hot_score": None, "hot_content": None}
    if not raw:
        return result

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return result

    if isinstance(data, dict):
        # Check for sub_title_list structure: {"sub_title_list": [{"content": "4732万", ...}]}
        sub_list = data.get("sub_title_list")
        if isinstance(sub_list, list):
            for item in sub_list:
                if isinstance(item, dict):
                    content = item.get("content")
                    if content:
                        parsed = _parse_text_for_hot(str(content))
                        if parsed["hot_content"] is not None:
                            return parsed

        # Direct keys
        result["hot_score"] = _to_float(data.get("hot_score") or data.get("score"))
        content = data.get("content") or data.get("hot_text") or data.get("text")
        if content:
            result["hot_content"] = str(content)
            if result["hot_score"] is None:
                parsed = _parse_text_for_hot(str(content))
                if parsed["hot_score"] is not None:
                    result["hot_score"] = parsed["hot_score"]
        return result

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                hs = _to_float(item.get("hot_score") or item.get("score"))
                content = item.get("content") or item.get("hot_text") or item.get("text")
                if hs is not None or content:
                    result["hot_score"] = hs
                    if content:
                        result["hot_content"] = str(content)
                    return result
            elif isinstance(item, str):
                parsed = _parse_text_for_hot(item)
                if parsed["hot_score"] is not None or parsed["hot_content"] is not None:
                    return parsed

    return result


def _parse_text_for_hot(text):
    result = {"hot_score": None, "hot_content": None}
    if not text:
        return result

    # Try to find patterns like "热度 1234万" or "1234万热度"
    match = re.search(r'([\d.]+)\s*万', text)
    if match:
        result["hot_content"] = text.strip()
        result["hot_score"] = float(match.group(1)) * 10000
        return result

    match = re.search(r'([\d.]+)\s*亿', text)
    if match:
        result["hot_content"] = text.strip()
        result["hot_score"] = float(match.group(1)) * 100000000
        return result

    match = re.search(r'(\d+)', text)
    if match:
        result["hot_content"] = text.strip()
        result["hot_score"] = float(match.group(1))

    return result


def hot_content_to_numeric(text):
    """Convert hot_content text like '1234万' to numeric value for sorting."""
    if not text:
        return None
    try:
        match = re.search(r'([\d.]+)\s*亿', text)
        if match:
            return int(float(match.group(1)) * 100000000)
        match = re.search(r'([\d.]+)\s*万', text)
        if match:
            return int(float(match.group(1)) * 10000)
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))
    except (ValueError, TypeError):
        pass
    return None


def _to_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_category_schema(raw):
    """Parse category_schema from ranking API for additional info like copyright."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}
