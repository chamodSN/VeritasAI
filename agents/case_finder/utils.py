import re
import unicodedata
from datetime import datetime, date


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).strip()
    return text


def parse_dates_smart(text: str):
    if not text:
        return None, None
    t = normalize_text(text.lower())
    year_match = re.search(r'\b(\d{4})\b', t)
    if year_match:
        year = int(year_match.group(1))
        if 1900 <= year <= 2100:
            return date(year, 1, 1).isoformat(), date(year, 12, 31).isoformat()

    date_patterns = r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2}|(?<![\d\w])(\d{4})(?![\d\w])|\w+\s+\d{1,2},?\s+\d{4}|\w+\s+\d{4}|last\s+\w+|this\s+\w+|between\s+.+?\s+and\s+.+?)\b'
    potential_dates = re.findall(date_patterns, t, re.I)

    parsed_dates = []
    for pd in potential_dates:
        if isinstance(pd, tuple):
            pd = pd[0]
        try:
            if re.match(r'^\d{4}$', pd):
                year = int(pd)
                dt = date(year, 1, 1)
            else:
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%B %d, %Y', '%b %d, %Y', '%Y']:
                    try:
                        dt = datetime.strptime(pd, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    continue
            parsed_dates.append(dt)
        except ValueError:
            continue

    between_match = re.search(
        r"between\s+(.+?)\s+and\s+(.+?)(?:\s|$)", t, re.I)
    if between_match:
        for part in [between_match.group(1), between_match.group(2)]:
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%B %d, %Y', '%b %d, %Y', '%Y']:
                try:
                    dt = datetime.strptime(part, fmt).date()
                    parsed_dates.append(dt)
                    break
                except ValueError:
                    continue

    parsed_dates = sorted(set(parsed_dates))

    if len(parsed_dates) >= 2:
        return parsed_dates[0].isoformat(), parsed_dates[-1].isoformat()
    elif len(parsed_dates) == 1:
        pd = parsed_dates[0]
        if pd.month == 1 and pd.day == 1 and 1900 <= pd.year <= 2100:
            return date(pd.year, 1, 1).isoformat(), date(pd.year, 12, 31).isoformat()
        return pd.isoformat(), pd.isoformat()
    else:
        yr_rng = re.search(
            r"\b(\d{4})\s*(?:to|\-|\u2013|\u2014)\s*(\d{4})\b", t)
        if yr_rng:
            y1, y2 = sorted([int(yr_rng.group(1)), int(yr_rng.group(2))])
            return date(y1, 1, 1).isoformat(), date(y2, 12, 31).isoformat()

    return None, None
