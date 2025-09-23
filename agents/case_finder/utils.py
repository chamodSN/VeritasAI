import re
import unicodedata
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import dateparser

ISO_FMT = "%Y-%m-%d"

RELATIVE_PATTERNS = [
    (re.compile(r"last\s+(\d+)\s+years?", re.I),
     lambda n: (date.today() - relativedelta(years=int(n)), date.today())),
    (re.compile(r"last\s+(\d+)\s+months?", re.I),
     lambda n: (date.today() - relativedelta(months=int(n)), date.today())),
    (re.compile(r"last\s+year", re.I), lambda _: (date(date.today().year -
     1, 1, 1), date(date.today().year-1, 12, 31))),
    (re.compile(r"this\s+year", re.I),
     lambda _: (date(date.today().year, 1, 1), date.today())),
    (re.compile(r"past\s+year", re.I),
     lambda _: (date.today()-relativedelta(years=1), date.today())),
]

QTR_PATTERN = re.compile(r"Q([1-4])\s*(\d{4})", re.I)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.strip()
    return text


def parse_dates_smart(text: str):
    if not text:
        return None, None

    t = normalize_text(text)

    m = QTR_PATTERN.search(t)
    if m:
        q = int(m.group(1))
        y = int(m.group(2))
        start_month = {1: 1, 2: 4, 3: 7, 4: 10}[q]
        start = date(y, start_month, 1)
        end = (start + relativedelta(months=3)) - timedelta(days=1)
        return start.isoformat(), end.isoformat()

    for pat, fn in RELATIVE_PATTERNS:
        m = pat.search(t)
        if m:
            arg = m.group(1) if m.groups() else None
            d1, d2 = fn(arg)
            return d1.isoformat(), d2.isoformat()

    between = re.search(r"between\s+(.+?)\s+and\s+(.+)$", t, flags=re.I)
    if between:
        d1 = dateparser.parse(between.group(1), settings={
                              'PREFER_DATES_FROM': 'past'})
        d2 = dateparser.parse(between.group(2), settings={
                              'PREFER_DATES_FROM': 'past'})
        if d1 and d2:
            a, b = sorted([d1.date(), d2.date()])
            return a.isoformat(), b.isoformat()

    after = re.search(r"\b(after|since)\s+(.+)$", t, flags=re.I)
    if after:
        d = dateparser.parse(after.group(2), settings={
                             'PREFER_DATES_FROM': 'past'})
        if d:
            return d.date().isoformat(), None

    before = re.search(r"\b(before|until|till)\s+(.+)$", t, flags=re.I)
    if before:
        d = dateparser.parse(before.group(2), settings={
                             'PREFER_DATES_FROM': 'past'})
        if d:
            return None, d.date().isoformat()

    parsed_dates = []
    for chunk in re.findall(r"\b([A-Za-z]{3,9} \d{1,2}, \d{4}|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{1,2}-\d{1,2}|[A-Za-z]{3,9} \d{4}|\d{4})\b", t):
        dt = dateparser.parse(chunk, settings={'PREFER_DATES_FROM': 'past'})
        if dt:
            parsed_dates.append(dt.date())

    if parsed_dates:
        parsed_dates.sort()
        start = parsed_dates[0]
        end = parsed_dates[-1] if len(parsed_dates) > 1 else None
        return start.isoformat(), end.isoformat() if end else None

    return None, None
