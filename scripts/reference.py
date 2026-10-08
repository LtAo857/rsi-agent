# 参考实现：只用于校验题库，绝不交给 Agent
import re
import heapq
from collections import OrderedDict, Counter
from datetime import date, timedelta


def _to_roman(n):
    out = ""
    for v, s in [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
                 (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]:
        while n >= v:
            out += s
            n -= v
    return out


_ROMAN = {_to_roman(i): i for i in range(1, 4000)}


def roman_to_int(s):
    return _ROMAN.get(s, -1)


def parse_duration(s):
    m = re.fullmatch(r"\s*(?:(\d+)d\s*)?(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s\s*)?", s)
    if not m or not any(m.groups()):
        raise ValueError(s)
    return sum(int(g or 0) * k for g, k in zip(m.groups(), (86400, 3600, 60, 1)))


def merge_intervals(intervals):
    out = []
    for a, b in sorted(intervals):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def compare_semver(a, b):
    def key(v):
        v = v.split("+")[0]
        core, _, pre = v.partition("-")
        nums = tuple(int(x) for x in core.split("."))
        if not pre:
            return nums, (1,)
        ids = tuple((0, int(x), "") if x.isdigit() else (1, 0, x) for x in pre.split("."))
        return nums, (0, ids)
    ka, kb = key(a), key(b)
    return (ka > kb) - (ka < kb)


def wrap_text(text, width):
    lines, cur = [], ""
    for w in text.split():
        if len(w) > width:
            if cur:
                lines.append(cur)
            chunks = [w[i:i + width] for i in range(0, len(w), width)]
            lines.extend(chunks[:-1])
            cur = chunks[-1]
        elif not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def eval_expr(s):
    toks = re.findall(r"\d+|[-+*/()]", s)
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def take():
        nonlocal pos
        pos += 1
        return toks[pos - 1]

    def expr():
        v = term()
        while peek() in ("+", "-"):
            v = v + term() if take() == "+" else v - term()
        return v

    def term():
        v = unary()
        while peek() in ("*", "/"):
            op, r = take(), unary()
            if op == "*":
                v *= r
            else:
                if r == 0:
                    raise ZeroDivisionError
                q = abs(v) // abs(r)
                v = q if (v >= 0) == (r >= 0) else -q
        return v

    def unary():
        if peek() in ("+", "-"):
            return unary() if take() == "+" else -unary()
        if peek() == "(":
            take()
            v = expr()
            take()
            return v
        return int(take())

    return expr()


class LRUCache:
    def __init__(self, capacity):
        self.cap, self.d = capacity, OrderedDict()

    def get(self, key):
        if key not in self.d:
            return -1
        self.d.move_to_end(key)
        return self.d[key]

    def put(self, key, value):
        if self.cap <= 0:
            return
        self.d[key] = value
        self.d.move_to_end(key)
        if len(self.d) > self.cap:
            self.d.popitem(last=False)


def rle_encode(s):
    return "".join(f"{len(m.group(0))}{m.group(1)}" for m in re.finditer(r"(.)\1*", s, re.S))


def rle_decode(s):
    return "".join(c * int(n) for n, c in re.findall(r"(\d+)(\D)", s))


def topo_sort(graph):
    nodes = set(graph) | {d for ds in graph.values() for d in ds}
    indeg = {n: 0 for n in nodes}
    users = {n: [] for n in nodes}
    for n, ds in graph.items():
        for d in ds:
            indeg[n] += 1
            users[d].append(n)
    heap = [n for n in nodes if indeg[n] == 0]
    heapq.heapify(heap)
    out = []
    while heap:
        n = heapq.heappop(heap)
        out.append(n)
        for u in users[n]:
            indeg[u] -= 1
            if indeg[u] == 0:
                heapq.heappush(heap, u)
    if len(out) != len(nodes):
        raise ValueError("cycle")
    return out


def normalize_path(p):
    absolute = p.startswith("/")
    parts = []
    for c in p.split("/"):
        if c in ("", "."):
            continue
        if c == "..":
            if parts and parts[-1] != "..":
                parts.pop()
            elif not absolute:
                parts.append("..")
        else:
            parts.append(c)
    if absolute:
        return "/" + "/".join(parts)
    return "/".join(parts) or "."


def split_csv_line(line):
    fields, i, n = [], 0, len(line)
    while True:
        if i < n and line[i] == '"':
            i += 1
            buf = ""
            while i < n:
                if line[i] == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        buf += '"'
                        i += 2
                        continue
                    i += 1
                    break
                buf += line[i]
                i += 1
            j = line.find(",", i)
            j = n if j == -1 else j
            buf += line[i:j]
        else:
            j = line.find(",", i)
            j = n if j == -1 else j
            buf = line[i:j]
        fields.append(buf)
        if j >= n:
            return fields
        i = j + 1


def next_permutation(nums):
    a = list(nums)
    i = len(a) - 2
    while i >= 0 and a[i] >= a[i + 1]:
        i -= 1
    if i < 0:
        return sorted(a)
    j = len(a) - 1
    while a[j] <= a[i]:
        j -= 1
    a[i], a[j] = a[j], a[i]
    a[i + 1:] = reversed(a[i + 1:])
    return a


_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def number_to_words(n):
    def below_1000(x):
        w = []
        if x >= 100:
            w += [_ONES[x // 100], "hundred"]
            x %= 100
        if x >= 20:
            w.append(_TENS[x // 10] + ("-" + _ONES[x % 10] if x % 10 else ""))
        elif x:
            w.append(_ONES[x])
        return w
    if n == 0:
        return "zero"
    w = []
    for scale, name in ((10**6, "million"), (10**3, "thousand"), (1, "")):
        if n >= scale:
            w += below_1000(n // scale) + ([name] if name else [])
            n %= scale
    return " ".join(w)


def spiral_order(matrix):
    m = [list(r) for r in matrix if r]
    out = []
    while m:
        out += m.pop(0)
        m = [list(r) for r in zip(*m)][::-1]
    return out


def longest_palindrome(s):
    best = ""
    for c in range(len(s)):
        for l, r in ((c, c), (c, c + 1)):
            while l >= 0 and r < len(s) and s[l] == s[r]:
                l -= 1
                r += 1
            if r - l - 1 > len(best):
                best = s[l + 1:r]
    return best


def is_balanced(s):
    stack, i, pairs = [], 0, {")": "(", "]": "[", "}": "{"}
    while i < len(s):
        ch = s[i]
        if ch == "'":
            i += 1
            while i < len(s) and s[i] != "'":
                i += 2 if s[i] == "\\" else 1
            if i >= len(s):
                return False
        elif ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
        i += 1
    return not stack


def business_days(start, end):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    if b < a:
        return -business_days(end, start)
    return sum((a + timedelta(d)).weekday() < 5 for d in range(1, (b - a).days + 1))


def cron_matches(expr, dt):
    def field(spec, lo, hi):
        vals = set()
        for part in spec.split(","):
            rng, _, step = part.partition("/")
            step = int(step) if step else 1
            if rng == "*":
                a, b = lo, hi
            elif "-" in rng:
                a, b = map(int, rng.split("-"))
            else:
                a = b = int(rng)
            vals.update(range(a, b + 1, step))
        return vals
    mi, h, dom, mon, dow = expr.split()
    days = field(dow, 0, 7)
    if 7 in days:
        days.add(0)
    dom_ok = dt.day in field(dom, 1, 31)
    dow_ok = (dt.weekday() + 1) % 7 in days
    if dom != "*" and dow != "*":
        day_ok = dom_ok or dow_ok
    else:
        day_ok = dom_ok and dow_ok
    return dt.minute in field(mi, 0, 59) and dt.hour in field(h, 0, 23) and dt.month in field(mon, 1, 12) and day_ok


def format_bytes(n):
    sign, x = ("-" if n < 0 else ""), abs(n)
    if x < 1024:
        return f"{n} B"
    units = ["KiB", "MiB", "GiB", "TiB", "PiB"]
    v, i = x / 1024, 0
    while i < len(units) - 1 and round(v, 1) >= 1024:
        v /= 1024
        i += 1
    return f"{sign}{v:.1f} {units[i]}"


def top_words(text, k):
    c = Counter(re.findall(r"[a-z]+(?:'[a-z]+)*", text.lower()))
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:k]


def min_coins(coins, amount):
    INF = float("inf")
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and dp[a - c] + 1 < dp[a]:
                dp[a] = dp[a - c] + 1
    return -1 if dp[amount] == INF else dp[amount]


def flatten(d):
    out = {}

    def walk(v, prefix):
        items = v.items() if isinstance(v, dict) else enumerate(v) if isinstance(v, list) else None
        if items is None or (prefix and not v):
            out[prefix] = v
            return
        for k, sub in items:
            walk(sub, f"{prefix}.{k}" if prefix else str(k))
    walk(d, "")
    return out


def valid_sudoku(board):
    if len(board) != 9 or any(len(r) != 9 or any(c not in ".123456789" for c in r) for r in board):
        return False
    seen = set()
    for i, row in enumerate(board):
        for j, c in enumerate(row):
            if c == ".":
                continue
            for k in (("r", i, c), ("c", j, c), ("b", i // 3, j // 3, c)):
                if k in seen:
                    return False
                seen.add(k)
    return True


def glob_match(pattern, s):
    def to_re(p):
        out, i = "", 0
        while i < len(p):
            ch = p[i]
            if ch == "*":
                out += ".*"
            elif ch == "?":
                out += "."
            elif ch == "[" and "]" in p[i + 2:] if p[i + 1:i + 2] == "!" else ch == "[" and "]" in p[i + 1:]:
                j = p.index("]", i + (2 if p[i + 1] == "!" else 1))
                body = p[i + 1:j]
                neg = body.startswith("!")
                body = body[1:] if neg else body
                out += "[" + ("^" if neg else "") + body.replace("\\", "\\\\") + "]"
                i = j
            else:
                out += re.escape(ch)
            i += 1
        return out
    return re.fullmatch(to_re(pattern), s, re.S) is not None


# ---- 第二批 ----
import bisect
import calendar
from urllib.parse import unquote_plus


def is_valid_luhn(s):
    s = s.replace(" ", "")
    if len(s) < 2 or not all(c in "0123456789" for c in s):
        return False
    total = 0
    for i, c in enumerate(reversed(s)):
        d = int(c)
        if i % 2:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
    return total % 10 == 0


def to_snake(name):
    out = []
    for i, c in enumerate(name):
        if c.isupper() and i > 0:
            prev, nxt = name[i - 1], name[i + 1] if i + 1 < len(name) else ""
            if prev.islower() or prev.isdigit() or (prev.isupper() and nxt.islower()):
                out.append("_")
        out.append(c.lower())
    return "".join(out)


def group_anagrams(words):
    groups = {}
    for w in words:
        groups.setdefault("".join(sorted(w)), []).append(w)
    return list(groups.values())


def kth_largest_distinct(nums, k):
    d = sorted(set(nums), reverse=True)
    return d[k - 1] if k <= len(d) else None


def isbn10_valid(s):
    s = s.replace("-", "")
    if len(s) != 10 or not s[:9].isdigit() or not (s[9].isdigit() or s[9] == "X"):
        return False
    vals = [int(c) for c in s[:9]] + [10 if s[9] == "X" else int(s[9])]
    return sum(v * (10 - i) for i, v in enumerate(vals)) % 11 == 0


def add_months(d, n):
    y, m, day = map(int, d.split("-"))
    idx = y * 12 + (m - 1) + n
    y, m = divmod(idx, 12)
    m += 1
    day = min(day, calendar.monthrange(y, m)[1])
    return f"{y:04d}-{m:02d}-{day:02d}"


def to_base(n, b):
    if not 2 <= b <= 36:
        raise ValueError(b)
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    sign, n, out = ("-" if n < 0 else ""), abs(n), ""
    while n:
        n, r = divmod(n, b)
        out = digits[r] + out
    return sign + out


def rotate_matrix(m):
    return [list(r) for r in zip(*m[::-1])]


def count_islands(grid):
    seen, count = set(), 0
    for i, row in enumerate(grid):
        for j, c in enumerate(row):
            if c == "1" and (i, j) not in seen:
                count += 1
                stack = [(i, j)]
                seen.add((i, j))
                while stack:
                    a, b = stack.pop()
                    for x, y in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                        if 0 <= x < len(grid) and 0 <= y < len(grid[x]) and grid[x][y] == "1" and (x, y) not in seen:
                            seen.add((x, y))
                            stack.append((x, y))
    return count


class RunningMedian:
    def __init__(self):
        self.v = []

    def add(self, x):
        bisect.insort(self.v, x)

    def median(self):
        if not self.v:
            raise ValueError("empty")
        n = len(self.v)
        return float(self.v[n // 2]) if n % 2 else (self.v[n // 2 - 1] + self.v[n // 2]) / 2


def summarize_ranges(nums):
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else f"{nums[i]}->{nums[j]}")
        i = j + 1
    return out


def bowling_score(rolls):
    total, i = 0, 0
    for _ in range(10):
        if rolls[i] == 10:
            total += 10 + rolls[i + 1] + rolls[i + 2]
            i += 1
        elif rolls[i] + rolls[i + 1] == 10:
            total += 10 + rolls[i + 2]
            i += 2
        else:
            total += rolls[i] + rolls[i + 1]
            i += 2
    return total


def humanize_seconds(n):
    if n < 0:
        raise ValueError(n)
    if n == 0:
        return "now"
    parts = []
    for name, size in (("year", 31536000), ("day", 86400), ("hour", 3600), ("minute", 60), ("second", 1)):
        c, n = divmod(n, size)
        if c:
            parts.append(f"{c} {name}" + ("s" if c != 1 else ""))
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def unique_preserve(seq):
    seen, out = set(), []
    for x in seq:
        try:
            if x in seen:
                continue
            seen.add(x)
        except TypeError:
            if x in out:
                continue
        out.append(x)
    return out


def parse_query(qs):
    if qs.startswith("?"):
        qs = qs[1:]
    out = {}
    for piece in qs.split("&"):
        if not piece:
            continue
        k, _, v = piece.partition("=")
        out.setdefault(unquote_plus(k), []).append(unquote_plus(v))
    return out


def eval_rpn(tokens):
    st = []
    for t in tokens:
        if t in ("+", "-", "*", "/"):
            if len(st) < 2:
                raise ValueError("underflow")
            b, a = st.pop(), st.pop()
            if t == "+":
                st.append(a + b)
            elif t == "-":
                st.append(a - b)
            elif t == "*":
                st.append(a * b)
            else:
                if b == 0:
                    raise ZeroDivisionError
                q = abs(a) // abs(b)
                st.append(q if (a >= 0) == (b >= 0) else -q)
        elif re.fullmatch(r"-?\d+", t):
            st.append(int(t))
        else:
            raise ValueError(t)
    if len(st) != 1:
        raise ValueError("bad stack")
    return st[0]


def sort_versions(vs):
    def key(v):
        parts = [int(x) for x in v.split(".")]
        while parts and parts[-1] == 0:
            parts.pop()
        return parts
    return sorted(vs, key=key)


def vigenere_encrypt(text, key):
    if not key or not all(c.isascii() and c.isalpha() for c in key):
        raise ValueError(key)
    shifts = [ord(c.lower()) - 97 for c in key]
    out, k = [], 0
    for c in text:
        if c.isascii() and c.isalpha():
            base = 65 if c.isupper() else 97
            out.append(chr((ord(c) - base + shifts[k % len(shifts)]) % 26 + base))
            k += 1
        else:
            out.append(c)
    return "".join(out)


def min_window(s, t):
    if not t:
        return ""
    need, missing = Counter(t), len(t)
    best, left = (0, 0), 0
    for right, c in enumerate(s, 1):
        if need[c] > 0:
            missing -= 1
        need[c] -= 1
        if missing == 0:
            while need[s[left]] < 0:
                need[s[left]] += 1
                left += 1
            if best == (0, 0) or right - left < best[1] - best[0]:
                best = (left, right)
            need[s[left]] += 1
            missing += 1
            left += 1
    return s[best[0]:best[1]]


def zigzag_convert(s, rows):
    if rows == 1:
        return s
    lines, r, step = [""] * rows, 0, 1
    for c in s:
        lines[r] += c
        if r == 0:
            step = 1
        elif r == rows - 1:
            step = -1
        r += step
    return "".join(lines)


def largest_rectangle(heights):
    st, best = [], 0
    for i, h in enumerate(heights + [0]):
        start = i
        while st and st[-1][1] >= h:
            j, hh = st.pop()
            best = max(best, hh * (i - j))
            start = j
        st.append((start, h))
    return best


def valid_ipv4(s):
    parts = s.split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not (1 <= len(p) <= 3) or not all(c in "0123456789" for c in p):
            return False
        if (len(p) > 1 and p[0] == "0") or int(p) > 255:
            return False
    return True


def get_path(obj, path):
    if path == "":
        return obj
    if not re.fullmatch(r"(?:[A-Za-z_]\w*|\[\d+\])(?:\.[A-Za-z_]\w*|\[\d+\])*", path):
        raise KeyError(path)
    cur = obj
    for key, idx in re.findall(r"([A-Za-z_]\w*)|\[(\d+)\]", path):
        if key:
            if not isinstance(cur, dict) or key not in cur:
                raise KeyError(key)
            cur = cur[key]
        else:
            i = int(idx)
            if not isinstance(cur, list) or i >= len(cur):
                raise KeyError(idx)
            cur = cur[i]
    return cur


def free_slots(busy, start, end):
    out, cur = [], start
    for s, e in sorted(busy):
        if e <= s:
            continue
        if s > cur:
            out.append([cur, min(s, end)])
        cur = max(cur, e)
        if cur >= end:
            break
    if cur < end:
        out.append([cur, end])
    return [g for g in out if g[0] < g[1]]
