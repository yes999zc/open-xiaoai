import json


def to_set(data):
    if isinstance(data, list):
        return list(set(data))
    return data


def json_encode(obj, pretty=False):
    try:
        return json.dumps(obj, ensure_ascii=False, indent=4 if pretty else None)
    except Exception as _:
        return None


def json_decode(text):
    try:
        return json.loads(text)
    except Exception:
        return None
