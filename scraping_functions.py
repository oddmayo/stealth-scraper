import re


def format_seconds(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def clean_name_text(value) -> str:
    """Keep only letters in a scraped name, preserving word boundaries."""
    if value is None:
        return ""

    parts = re.findall(r"[^\W\d_]+", str(value), flags=re.UNICODE)
    return " ".join(parts).strip()


def clean_price_text(value) -> str:
    """Normalize a scraped price to digits with a single decimal point.

    Handles common formats such as:
    - $1,159.69 -> 1159.69
    - 1.159,69 -> 1159.69
    - 1 159,69 -> 1159.69
    - 1159 -> 1159
    """
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    candidate_match = re.findall(r"[+-]?\d[\d\s,\.']*\d|[+-]?\d", text)
    if not candidate_match:
        return ""

    candidate = candidate_match[0]
    candidate = candidate.replace(" ", "").replace("'", "")

    sign = ""
    if candidate.startswith(("+", "-")):
        sign = "-" if candidate[0] == "-" else ""
        candidate = candidate[1:]

    candidate = re.sub(r"[^0-9,\.]+", "", candidate)
    if not candidate:
        return ""

    has_dot = "." in candidate
    has_comma = "," in candidate

    if has_dot and has_comma:
        decimal_sep = "." if candidate.rfind(".") > candidate.rfind(",") else ","
        thousands_sep = "," if decimal_sep == "." else "."
        candidate = candidate.replace(thousands_sep, "")
        candidate = candidate.replace(decimal_sep, ".")
    elif has_dot or has_comma:
        sep = "." if has_dot else ","
        groups = candidate.split(sep)

        if len(groups) == 2:
            trailing = groups[1]
            if len(trailing) in (1, 2):
                candidate = f"{groups[0]}.{trailing}"
            elif len(trailing) == 3:
                candidate = "".join(groups)
            else:
                candidate = f"{groups[0]}.{trailing}"
        else:
            trailing = groups[-1]
            if len(trailing) in (1, 2):
                candidate = "".join(groups[:-1]) + f".{trailing}"
            else:
                candidate = "".join(groups)

    candidate = re.sub(r"[^0-9\.]+", "", candidate)
    candidate = re.sub(r"\.(?=.*\.)", "", candidate)
    candidate = candidate.strip(".")

    return f"{sign}{candidate}" if candidate else ""

