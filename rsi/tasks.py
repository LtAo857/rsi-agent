"""评测题库（锁定文件，进化过程中不可修改）。

每道题：
  prompt   给 Agent 看的题面
  entry    需要实现的函数/类名
  visible  Agent 可以自测的样例（通过 tools.run_tests）
  hidden   只在评测时使用，Agent 看不到
每条测试是一段 Python 代码，执行不抛异常即通过；可用 _raises(exc, fn, *args) 和 datetime。
"""

TASKS = [
    dict(id="roman", entry="roman_to_int", prompt="""\
Write `roman_to_int(s: str) -> int` that converts a Roman numeral to an integer.
Only canonical (standard, minimal) uppercase numerals for 1..3999 are valid, e.g. 4 is "IV" (never "IIII"),
49 is "XLIX" (never "IL"). Return -1 for any invalid or non-canonical input, including the empty string.""",
         visible=["assert roman_to_int('XIV') == 14", "assert roman_to_int('MCMXCIV') == 1994"],
         hidden=["assert roman_to_int('IIII') == -1", "assert roman_to_int('IC') == -1",
                 "assert roman_to_int('VX') == -1", "assert roman_to_int('') == -1",
                 "assert roman_to_int('MMMCMXCIX') == 3999", "assert roman_to_int('MMMM') == -1",
                 "assert roman_to_int('xiv') == -1", "assert roman_to_int('XLIX') == 49",
                 "assert roman_to_int('IL') == -1", "assert roman_to_int('CD') == 400",
                 "assert roman_to_int('DD') == -1"]),

    dict(id="duration", entry="parse_duration", prompt="""\
Write `parse_duration(s: str) -> int` returning the total number of seconds.
The input is one or more components `<non-negative integer><unit>` with units d (86400s), h, m, s.
Units must appear in the order d, h, m, s, each at most once. There is no space between a number and its unit,
but components may be separated by whitespace, and leading/trailing whitespace is allowed.
Raise ValueError for anything else (empty input, unknown unit, wrong order, repeated unit, decimals, signs).""",
         visible=["assert parse_duration('1h30m') == 5400", "assert parse_duration('45s') == 45"],
         hidden=["assert parse_duration('2d 3h') == 183600", "assert parse_duration(' 1d2h3m4s ') == 93784",
                 "assert parse_duration('0s') == 0", "assert parse_duration('90m') == 5400",
                 "assert _raises(ValueError, parse_duration, '')", "assert _raises(ValueError, parse_duration, '1x')",
                 "assert _raises(ValueError, parse_duration, '30m1h')", "assert _raises(ValueError, parse_duration, '1h1h')",
                 "assert _raises(ValueError, parse_duration, 'h')", "assert _raises(ValueError, parse_duration, '1.5h')",
                 "assert _raises(ValueError, parse_duration, '-1h')", "assert _raises(ValueError, parse_duration, '1 h')"]),

    dict(id="intervals", entry="merge_intervals", prompt="""\
Write `merge_intervals(intervals: list[list[int]]) -> list[list[int]]`.
Each interval is [start, end] with start <= end. Merge intervals that overlap OR touch (end == next start).
Input may be unsorted. Return the merged intervals sorted by start. Do not mutate the input.""",
         visible=["assert merge_intervals([[1,3],[2,6],[8,10]]) == [[1,6],[8,10]]"],
         hidden=["assert merge_intervals([]) == []", "assert merge_intervals([[1,2],[2,3]]) == [[1,3]]",
                 "assert merge_intervals([[5,6],[1,2]]) == [[1,2],[5,6]]",
                 "assert merge_intervals([[1,10],[2,3]]) == [[1,10]]",
                 "assert merge_intervals([[3,3],[3,3]]) == [[3,3]]",
                 "x = [[2,3],[1,2]]\nmerge_intervals(x)\nassert x == [[2,3],[1,2]]"]),

    dict(id="semver", entry="compare_semver", prompt="""\
Write `compare_semver(a: str, b: str) -> int` returning -1, 0 or 1 according to Semantic Versioning 2.0.0
precedence rules, including pre-release versions (e.g. 1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-beta < 1.0.0).
Build metadata (anything after '+') is ignored.""",
         visible=["assert compare_semver('1.0.0', '2.0.0') == -1", "assert compare_semver('1.2.3', '1.2.3') == 0"],
         hidden=["assert compare_semver('1.0.0-alpha', '1.0.0') == -1",
                 "assert compare_semver('1.0.0-alpha', '1.0.0-alpha.1') == -1",
                 "assert compare_semver('1.0.0-alpha.1', '1.0.0-alpha.beta') == -1",
                 "assert compare_semver('1.0.0-beta.2', '1.0.0-beta.11') == -1",
                 "assert compare_semver('1.0.0-rc.1', '1.0.0-beta.11') == 1",
                 "assert compare_semver('1.0.0+build', '1.0.0') == 0",
                 "assert compare_semver('1.10.0', '1.9.0') == 1",
                 "assert compare_semver('1.0.0-alpha.1+x', '1.0.0-alpha.1') == 0"]),

    dict(id="wrap", entry="wrap_text", prompt="""\
Write `wrap_text(text: str, width: int) -> list[str]`.
Split text on any whitespace into words and fill lines greedily, joining words with a single space, so that
every line has length <= width. A word longer than width starts on a new line (if the current line is non-empty)
and is cut into chunks of exactly `width` characters; its last chunk becomes the current line and may be followed
by further words. Return [] for empty or whitespace-only text.""",
         visible=["assert wrap_text('the quick brown fox', 10) == ['the quick', 'brown fox']"],
         hidden=["assert wrap_text('', 5) == []", "assert wrap_text('a b c d', 3) == ['a b', 'c d']",
                 "assert wrap_text('abcdefghij', 4) == ['abcd', 'efgh', 'ij']",
                 "assert wrap_text('hi abcdefghij x', 4) == ['hi', 'abcd', 'efgh', 'ij x']",
                 "assert wrap_text('  lots   of   space ', 20) == ['lots of space']",
                 "assert wrap_text('exactly', 7) == ['exactly']"]),

    dict(id="expr", entry="eval_expr", prompt="""\
Write `eval_expr(s: str) -> int` evaluating an integer arithmetic expression with + - * / and parentheses,
unary + and -, and arbitrary whitespace. Usual precedence, left associativity.
`/` is integer division that truncates toward zero (like C), e.g. -7/2 == -3. Division by zero raises ZeroDivisionError.""",
         visible=["assert eval_expr('1 + 2 * 3') == 7", "assert eval_expr('(1+2)*3') == 9"],
         hidden=["assert eval_expr('-(2+3)*-2') == 10", "assert eval_expr('2--3') == 5",
                 "assert eval_expr('10-4-3') == 3", "assert eval_expr('  7 ') == 7",
                 "assert eval_expr('-2*-2*-2') == -8", "assert eval_expr('+-+1') == -1",
                 "assert eval_expr('1-(2-(3-4))') == -2", "assert eval_expr('7/2') == 3",
                 "assert eval_expr('-7/2') == -3", "assert eval_expr('7/-2') == -3",
                 "assert eval_expr('2*3/4') == 1", "assert _raises(ZeroDivisionError, eval_expr, '1/0')"]),

    dict(id="lru", entry="LRUCache", prompt="""\
Implement class `LRUCache(capacity: int)` with `get(key) -> value` (returns -1 if missing) and `put(key, value)`.
Both get and put mark the key as most recently used; putting an existing key updates its value.
When inserting beyond capacity, evict the least recently used key. Capacity 0 stores nothing.""",
         visible=["c = LRUCache(2); c.put(1, 1); c.put(2, 2)\nassert c.get(1) == 1\nc.put(3, 3)\nassert c.get(2) == -1"],
         hidden=["c = LRUCache(0); c.put(1, 1)\nassert c.get(1) == -1",
                 "c = LRUCache(2); c.put(1, 1); c.put(2, 2); c.put(1, 10); c.put(3, 3)\nassert c.get(1) == 10 and c.get(2) == -1 and c.get(3) == 3",
                 "c = LRUCache(1); c.put(1, 1); c.put(2, 2)\nassert c.get(1) == -1 and c.get(2) == 2",
                 "c = LRUCache(2); c.put(1, 1); c.put(2, 2); c.get(1); c.put(3, 3)\nassert c.get(1) == 1 and c.get(2) == -1",
                 "c = LRUCache(2)\nassert c.get(42) == -1"]),

    dict(id="rle", entry="rle_encode", prompt="""\
Write `rle_encode(s: str) -> str` and `rle_decode(s: str) -> str` (run-length encoding).
Encoding writes each maximal run as `<count><char>`, always including the count (e.g. "aaab" -> "3a1b",
12 a's -> "12a"). The input to rle_encode never contains digits but may contain any other characters
(spaces, punctuation, unicode). rle_decode is the exact inverse. Empty string maps to empty string.""",
         visible=["assert rle_encode('aaab') == '3a1b'", "assert rle_decode('3a1b') == 'aaab'"],
         hidden=["assert rle_encode('') == ''", "assert rle_decode('') == ''",
                 "assert rle_encode('a' * 12) == '12a'", "assert rle_decode('12a3b') == 'a' * 12 + 'bbb'",
                 "assert rle_encode('  !') == '2 1!'", "assert rle_encode('ééx') == '2é1x'",
                 "assert rle_decode(rle_encode('hello, world!!')) == 'hello, world!!'",
                 "assert rle_encode('abab') == '1a1b1a1b'"]),

    dict(id="topo", entry="topo_sort", prompt="""\
Write `topo_sort(graph: dict[str, list[str]]) -> list[str]`. graph[n] lists the nodes n depends on (they must
come before n). Nodes that only appear in dependency lists are included too. Among all valid orders return the
lexicographically smallest one (always pick the smallest available node next). Raise ValueError on a cycle.""",
         visible=["assert topo_sort({'b': ['a'], 'a': []}) == ['a', 'b']"],
         hidden=["assert topo_sort({'c': ['a', 'b'], 'b': [], 'a': []}) == ['a', 'b', 'c']",
                 "assert topo_sort({'x': ['y']}) == ['y', 'x']", "assert topo_sort({}) == []",
                 "assert _raises(ValueError, topo_sort, {'a': ['b'], 'b': ['a']})",
                 "assert _raises(ValueError, topo_sort, {'a': ['a']})",
                 "assert topo_sort({'d': ['b'], 'c': ['a'], 'b': [], 'a': []}) == ['a', 'b', 'c', 'd']",
                 "assert topo_sort({'b': [], 'a': ['c'], 'c': []}) == ['b', 'c', 'a']"]),

    dict(id="path", entry="normalize_path", prompt="""\
Write `normalize_path(p: str) -> str` normalizing a Unix path: collapse repeated slashes, drop '.', resolve '..'.
For absolute paths, '..' at the root stays at the root. For relative paths, leading '..' components that cannot
be resolved are kept. Any number of leading slashes means a single '/'. No trailing slash except for '/' itself.
An empty result for a relative path is '.'.""",
         visible=["assert normalize_path('/a/./b/../c/') == '/a/c'"],
         hidden=["assert normalize_path('') == '.'", "assert normalize_path('/../..') == '/'",
                 "assert normalize_path('a/../..') == '..'", "assert normalize_path('../x/../../y') == '../../y'",
                 "assert normalize_path('//a//b') == '/a/b'", "assert normalize_path('./') == '.'",
                 "assert normalize_path('a/b/..') == 'a'", "assert normalize_path('/') == '/'"]),

    dict(id="csv", entry="split_csv_line", prompt="""\
Write `split_csv_line(line: str) -> list[str]` splitting one CSV line on commas.
A field that STARTS with a double quote is quoted: inside it commas are literal and "" is a literal quote.
Quotes elsewhere are ordinary characters. Whitespace is preserved. An empty line gives [''];
a trailing comma gives a trailing empty field.""",
         visible=["assert split_csv_line('a,b,c') == ['a', 'b', 'c']", "assert split_csv_line('\"x,y\",z') == ['x,y', 'z']"],
         hidden=["assert split_csv_line('') == ['']", "assert split_csv_line('a,') == ['a', '']",
                 "assert split_csv_line('\"he said \"\"hi\"\"\",2') == ['he said \"hi\"', '2']",
                 "assert split_csv_line(' a , b ') == [' a ', ' b ']",
                 "assert split_csv_line('\"\",x') == ['', 'x']",
                 "assert split_csv_line('a\"b,c') == ['a\"b', 'c']",
                 "assert split_csv_line(',,') == ['', '', '']"]),

    dict(id="nextperm", entry="next_permutation", prompt="""\
Write `next_permutation(nums: list[int]) -> list[int]` returning (as a new list, without mutating the input)
the next lexicographically greater permutation. If nums is already the greatest, return it sorted ascending.
Duplicates are allowed.""",
         visible=["assert next_permutation([1, 2, 3]) == [1, 3, 2]"],
         hidden=["assert next_permutation([3, 2, 1]) == [1, 2, 3]", "assert next_permutation([1, 1, 5]) == [1, 5, 1]",
                 "assert next_permutation([1, 5, 1]) == [5, 1, 1]", "assert next_permutation([]) == []",
                 "assert next_permutation([1]) == [1]", "assert next_permutation([2, 3, 1]) == [3, 1, 2]",
                 "x = [1, 2, 3]\nnext_permutation(x)\nassert x == [1, 2, 3]"]),

    dict(id="words", entry="number_to_words", prompt="""\
Write `number_to_words(n: int) -> str` for 0 <= n < 1_000_000_000, in lowercase American English.
Words are separated by single spaces; numbers 21-99 that are not multiples of ten use a hyphen ("twenty-one").
No "and", no commas. Scale words: hundred, thousand, million. 0 is "zero".""",
         visible=["assert number_to_words(0) == 'zero'", "assert number_to_words(123) == 'one hundred twenty-three'"],
         hidden=["assert number_to_words(1000) == 'one thousand'", "assert number_to_words(1000001) == 'one million one'",
                 "assert number_to_words(90) == 'ninety'", "assert number_to_words(115) == 'one hundred fifteen'",
                 "assert number_to_words(999999999) == 'nine hundred ninety-nine million nine hundred ninety-nine thousand nine hundred ninety-nine'",
                 "assert number_to_words(100000) == 'one hundred thousand'", "assert number_to_words(40) == 'forty'",
                 "assert number_to_words(1000010) == 'one million ten'"]),

    dict(id="spiral", entry="spiral_order", prompt="""\
Write `spiral_order(matrix: list[list[int]]) -> list[int]` returning elements in clockwise spiral order starting
at the top-left. The matrix may be rectangular or empty.""",
         visible=["assert spiral_order([[1,2,3],[4,5,6],[7,8,9]]) == [1,2,3,6,9,8,7,4,5]"],
         hidden=["assert spiral_order([]) == []", "assert spiral_order([[]]) == []",
                 "assert spiral_order([[1],[2],[3]]) == [1,2,3]", "assert spiral_order([[1,2,3,4]]) == [1,2,3,4]",
                 "assert spiral_order([[1,2],[3,4],[5,6]]) == [1,2,4,6,5,3]",
                 "assert spiral_order([[1,2,3,4],[5,6,7,8],[9,10,11,12]]) == [1,2,3,4,8,12,11,10,9,5,6,7]"]),

    dict(id="palin", entry="longest_palindrome", prompt="""\
Write `longest_palindrome(s: str) -> str` returning the longest palindromic substring.
If several have the maximum length, return the one that starts earliest.""",
         visible=["assert longest_palindrome('babad') == 'bab'"],
         hidden=["assert longest_palindrome('cbbd') == 'bb'", "assert longest_palindrome('') == ''",
                 "assert longest_palindrome('a') == 'a'", "assert longest_palindrome('abcd') == 'a'",
                 "assert longest_palindrome('forgeeksskeegfor') == 'geeksskeeg'",
                 "assert longest_palindrome('abacdfgdcaba') == 'aba'", "assert longest_palindrome('aaaa') == 'aaaa'"]),

    dict(id="balanced", entry="is_balanced", prompt="""\
Write `is_balanced(s: str) -> bool` checking that brackets ()[]{} are balanced and properly nested.
Characters inside single-quoted string literals ('...') are ignored. Inside a quoted literal a backslash escapes
the next character. Outside quotes a backslash is an ordinary character. An unterminated quote makes the string
unbalanced.""",
         visible=["assert is_balanced('([]{})') is True", "assert is_balanced('(]') is False"],
         hidden=["assert is_balanced(\"('(')\") is True", "assert is_balanced(\"'unterminated\") is False",
                 "assert is_balanced(\"(')')\") is True", "assert is_balanced(\"('\\\\'')\") is True",
                 "assert is_balanced('') is True", "assert is_balanced('((') is False",
                 "assert is_balanced('a)b(') is False", "assert is_balanced('[\\\\(]') is False"]),

    dict(id="bizdays", entry="business_days", prompt="""\
Write `business_days(start: str, end: str) -> int` for ISO dates 'YYYY-MM-DD'. Count the weekdays (Mon-Fri)
in the half-open range (start, end] — start excluded, end included. If end < start, return
-business_days(end, start). No holidays.""",
         visible=["assert business_days('2024-01-01', '2024-01-08') == 5", "assert business_days('2024-01-05', '2024-01-05') == 0"],
         hidden=["assert business_days('2024-01-05', '2024-01-07') == 0",
                 "assert business_days('2024-01-06', '2024-01-08') == 1",
                 "assert business_days('2024-01-08', '2024-01-01') == -5",
                 "assert business_days('2024-02-28', '2024-03-01') == 2",
                 "assert business_days('2023-12-29', '2024-01-02') == 2",
                 "assert business_days('2020-01-01', '2025-01-01') == 1305"]),

    dict(id="cron", entry="cron_matches", prompt="""\
Write `cron_matches(expr: str, dt: datetime) -> bool` for 5-field cron expressions
"minute hour day-of-month month day-of-week". Each field supports '*', numbers, ranges 'a-b', steps '*/n' and
'a-b/n', and comma-separated lists of these. Day-of-week is 0-7 where both 0 and 7 mean Sunday.
Like Vixie cron: if BOTH day-of-month and day-of-week are restricted (not '*'), the date matches if EITHER matches.""",
         visible=["assert cron_matches('* * * * *', datetime(2024, 1, 1, 0, 0)) is True",
                  "assert cron_matches('30 9 * * *', datetime(2024, 1, 1, 9, 30)) is True"],
         hidden=["assert cron_matches('*/15 * * * *', datetime(2024, 1, 1, 10, 45)) is True",
                 "assert cron_matches('*/15 * * * *', datetime(2024, 1, 1, 10, 46)) is False",
                 "assert cron_matches('0 9-17/2 * * *', datetime(2024, 1, 1, 11, 0)) is True",
                 "assert cron_matches('0 9-17/2 * * *', datetime(2024, 1, 1, 12, 0)) is False",
                 "assert cron_matches('0 0 * * 7', datetime(2024, 1, 7, 0, 0)) is True",
                 "assert cron_matches('0 0 * * 0', datetime(2024, 1, 7, 0, 0)) is True",
                 "assert cron_matches('0 0 1 * 1', datetime(2024, 1, 8, 0, 0)) is True",
                 "assert cron_matches('0 0 1 * 1', datetime(2024, 1, 9, 0, 0)) is False",
                 "assert cron_matches('0 0 1,15 * *', datetime(2024, 3, 15, 0, 0)) is True",
                 "assert cron_matches('0 0 * 2 *', datetime(2024, 3, 1, 0, 0)) is False",
                 "assert cron_matches('5,10-12 * * * *', datetime(2024, 1, 1, 3, 11)) is True"]),

    dict(id="bytes", entry="format_bytes", prompt="""\
Write `format_bytes(n: int) -> str` using binary units B, KiB, MiB, GiB, TiB, PiB.
If |n| < 1024 return f"{n} B". Otherwise divide by 1024 until the value is < 1024 (stop at PiB) and format with
exactly one decimal, e.g. "1.5 KiB". If rounding to one decimal yields 1024.0, use the next unit instead
(e.g. 1048575 -> "1.0 MiB"). Negative numbers get a leading '-'.""",
         visible=["assert format_bytes(0) == '0 B'", "assert format_bytes(1536) == '1.5 KiB'"],
         hidden=["assert format_bytes(1023) == '1023 B'", "assert format_bytes(1024) == '1.0 KiB'",
                 "assert format_bytes(1048575) == '1.0 MiB'", "assert format_bytes(1048576) == '1.0 MiB'",
                 "assert format_bytes(-2048) == '-2.0 KiB'", "assert format_bytes(1024**5 * 2048) == '2048.0 PiB'",
                 "assert format_bytes(1024**3 * 5 + 1024**3 // 2) == '5.5 GiB'"]),

    dict(id="topwords", entry="top_words", prompt="""\
Write `top_words(text: str, k: int) -> list[tuple[str, int]]`. Words are maximal runs of ASCII letters,
case-insensitive (lowercased), that may contain internal apostrophes between letters (e.g. "don't", "rock'n'roll").
Return the k most frequent (word, count) pairs sorted by count descending, then word ascending.""",
         visible=["assert top_words('the cat the dog', 2) == [('the', 2), ('cat', 1)]"],
         hidden=["assert top_words(\"Don't stop, don't!\", 1) == [(\"don't\", 2)]", "assert top_words('', 3) == []",
                 "assert top_words('b a B A c', 5) == [('a', 2), ('b', 2), ('c', 1)]",
                 "assert top_words(\"'quoted' words\", 3) == [('quoted', 1), ('words', 1)]",
                 "assert top_words('x1y x', 2) == [('x', 2), ('y', 1)]",
                 "assert top_words(\"rock'n'roll rock\", 2) == [('rock', 1), (\"rock'n'roll\", 1)]"]),

    dict(id="coins", entry="min_coins", prompt="""\
Write `min_coins(coins: list[int], amount: int) -> int` returning the fewest coins (unlimited supply of each
denomination) that sum to amount, or -1 if impossible. amount 0 needs 0 coins.""",
         visible=["assert min_coins([1, 2, 5], 11) == 3"],
         hidden=["assert min_coins([2], 3) == -1", "assert min_coins([1], 0) == 0", "assert min_coins([], 0) == 0",
                 "assert min_coins([], 1) == -1", "assert min_coins([186, 419, 83, 408], 6249) == 20",
                 "assert min_coins([5, 3], 7) == -1", "assert min_coins([1, 3, 4], 6) == 2"]),

    dict(id="flatten", entry="flatten", prompt="""\
Write `flatten(d: dict) -> dict` flattening nested dicts and lists into a single dict with dotted string keys.
List elements use their index as the key segment. Keys are converted with str(). Empty dicts and empty lists
are kept as values at their key (not dropped). Do not mutate the input.""",
         visible=["assert flatten({'a': {'b': 1}}) == {'a.b': 1}"],
         hidden=["assert flatten({'a': [1, {'b': 2}]}) == {'a.0': 1, 'a.1.b': 2}", "assert flatten({}) == {}",
                 "assert flatten({'a': {}}) == {'a': {}}", "assert flatten({'a': []}) == {'a': []}",
                 "assert flatten({'x': {'y': {'z': None}}}) == {'x.y.z': None}",
                 "assert flatten({1: {2: 3}}) == {'1.2': 3}",
                 "x = {'a': {'b': [1]}}\nflatten(x)\nassert x == {'a': {'b': [1]}}"]),

    dict(id="sudoku", entry="valid_sudoku", prompt="""\
Write `valid_sudoku(board: list[str]) -> bool`. A board is exactly 9 strings of exactly 9 characters, each
character a digit 1-9 or '.' for empty. Return True if the board is well-formed and no digit repeats in any row,
column or 3x3 box (the board need not be solvable). Return False otherwise.""",
         visible=["assert valid_sudoku(['53..7....','6..195...','.98....6.','8...6...3','4..8.3..1','7...2...6','.6....28.','...419..5','....8..79']) is True"],
         hidden=["assert valid_sudoku(['.........'] * 9) is True",
                 "assert valid_sudoku(['53..7....','6..195...','..5....6.','8...6...3','4..8.3..1','7...2...6','.6....28.','...419..5','....8..79']) is False",
                 "assert valid_sudoku(['53..7....','6..195...','.98....6.','8...6...3','4..8.3..1','7...2...6','.6....28.','...419..5','5...8..79']) is False",
                 "assert valid_sudoku(['53..7...0','6..195...','.98....6.','8...6...3','4..8.3..1','7...2...6','.6....28.','...419..5','....8..79']) is False",
                 "assert valid_sudoku(['.........'] * 8) is False",
                 "assert valid_sudoku(['........'] * 9) is False"]),

    dict(id="glob", entry="glob_match", prompt="""\
Write `glob_match(pattern: str, s: str) -> bool` for whole-string glob matching: '*' matches any sequence
(including empty), '?' one character, '[abc]' a set, '[a-z]' a range, '[!...]' a negated set.
There are no escapes. A '[' without a closing ']' is a literal '['.""",
         visible=["assert glob_match('*.py', 'main.py') is True", "assert glob_match('?at', 'cat') is True"],
         hidden=["assert glob_match('*.py', 'main.pyc') is False", "assert glob_match('[!a-c]at', 'bat') is False",
                 "assert glob_match('[!a-c]at', 'zat') is True", "assert glob_match('a*b*c', 'aXbYc') is True",
                 "assert glob_match('a*b*c', 'acb') is False", "assert glob_match('', '') is True",
                 "assert glob_match('*', '') is True", "assert glob_match('[a-', '[a-') is True",
                 "assert glob_match('**a', 'bba') is True", "assert glob_match('file[0-9].txt', 'file7.txt') is True",
                 "assert glob_match('?', '') is False"]),
]

# ---- 第二批 24 题：扩大题量以降低评测噪声 ----
TASKS += [
    dict(id="luhn", entry="is_valid_luhn", prompt="""\
Write `is_valid_luhn(s: str) -> bool` validating a number with the Luhn checksum.
Spaces anywhere are allowed and ignored. Any other non-digit character makes it invalid.
After removing spaces, strings with fewer than 2 digits are invalid.""",
         visible=["assert is_valid_luhn('4539 3195 0343 6467') is True", "assert is_valid_luhn('8273 1232 7352 0569') is False"],
         hidden=["assert is_valid_luhn('0') is False", "assert is_valid_luhn(' 0 0 ') is True",
                 "assert is_valid_luhn('059') is True", "assert is_valid_luhn('059a') is False",
                 "assert is_valid_luhn('055 444 285') is True", "assert is_valid_luhn('091') is True",
                 "assert is_valid_luhn('-1') is False", "assert is_valid_luhn('   ') is False"]),

    dict(id="camel", entry="to_snake", prompt="""\
Write `to_snake(name: str) -> str` converting camelCase / PascalCase to snake_case.
Insert an underscore before an uppercase letter if it is preceded by a lowercase letter or a digit, OR if it is
preceded by an uppercase letter and followed by a lowercase letter (so acronyms stay together: "HTTPServer" ->
"http_server"). Existing underscores are kept. Then lowercase everything.""",
         visible=["assert to_snake('helloWorld') == 'hello_world'", "assert to_snake('HTTPServerError') == 'http_server_error'"],
         hidden=["assert to_snake('getHTTP') == 'get_http'", "assert to_snake('simple') == 'simple'",
                 "assert to_snake('already_snake') == 'already_snake'", "assert to_snake('Version2Update') == 'version2_update'",
                 "assert to_snake('ABC') == 'abc'", "assert to_snake('aB') == 'a_b'",
                 "assert to_snake('XMLHttpRequest') == 'xml_http_request'", "assert to_snake('') == ''",
                 "assert to_snake('A') == 'a'"]),

    dict(id="anagram", entry="group_anagrams", prompt="""\
Write `group_anagrams(words: list[str]) -> list[list[str]]` grouping words that are anagrams of each other
(exact, case-sensitive characters). Groups are ordered by the first appearance of any of their words; words
inside a group keep input order; duplicates are kept.""",
         visible=["assert group_anagrams(['eat','tea','tan','ate','nat','bat']) == [['eat','tea','ate'],['tan','nat'],['bat']]"],
         hidden=["assert group_anagrams([]) == []", "assert group_anagrams(['']) == [['']]",
                 "assert group_anagrams(['a','A']) == [['a'],['A']]", "assert group_anagrams(['ab','ba','ab']) == [['ab','ba','ab']]",
                 "assert group_anagrams(['abc','def','cab','fed']) == [['abc','cab'],['def','fed']]"]),

    dict(id="kthdistinct", entry="kth_largest_distinct", prompt="""\
Write `kth_largest_distinct(nums: list[int], k: int) -> int | None` returning the k-th largest DISTINCT value
(k >= 1), or None if there are fewer than k distinct values.""",
         visible=["assert kth_largest_distinct([3,1,2,4], 2) == 3"],
         hidden=["assert kth_largest_distinct([3,3,2], 2) == 2", "assert kth_largest_distinct([3,3,2], 3) is None",
                 "assert kth_largest_distinct([], 1) is None", "assert kth_largest_distinct([-1,-1,-2], 1) == -1",
                 "assert kth_largest_distinct([5,1,5,1,3], 2) == 3", "assert kth_largest_distinct([1], 1) == 1"]),

    dict(id="isbn", entry="isbn10_valid", prompt="""\
Write `isbn10_valid(s: str) -> bool`. Hyphens are ignored. The remaining string must be exactly 10 characters:
9 digits followed by a digit or an uppercase 'X' (meaning 10). Valid if (10*d1 + 9*d2 + ... + 1*d10) % 11 == 0.""",
         visible=["assert isbn10_valid('3-598-21508-8') is True", "assert isbn10_valid('3-598-21508-9') is False"],
         hidden=["assert isbn10_valid('3-598-21507-X') is True", "assert isbn10_valid('3-598-2X507-9') is False",
                 "assert isbn10_valid('359821507X') is True", "assert isbn10_valid('3-598-21507-x') is False",
                 "assert isbn10_valid('3598215088') is True", "assert isbn10_valid('') is False",
                 "assert isbn10_valid('3-598-21508-88') is False", "assert isbn10_valid('3-598-21508') is False"]),

    dict(id="addmonths", entry="add_months", prompt="""\
Write `add_months(d: str, n: int) -> str` adding n months (n may be negative or zero) to an ISO date 'YYYY-MM-DD'.
If the day does not exist in the target month, clamp it to that month's last day. Return ISO format.""",
         visible=["assert add_months('2024-01-31', 1) == '2024-02-29'", "assert add_months('2024-03-15', -2) == '2024-01-15'"],
         hidden=["assert add_months('2023-01-31', 1) == '2023-02-28'", "assert add_months('2024-12-31', 1) == '2025-01-31'",
                 "assert add_months('2024-01-15', -1) == '2023-12-15'", "assert add_months('2024-05-31', -3) == '2024-02-29'",
                 "assert add_months('2024-02-29', 12) == '2025-02-28'", "assert add_months('2024-06-10', 0) == '2024-06-10'",
                 "assert add_months('2024-01-01', -25) == '2021-12-01'"]),

    dict(id="tobase", entry="to_base", prompt="""\
Write `to_base(n: int, b: int) -> str` converting an integer to base b (2..36) using digits 0-9 then lowercase a-z.
Negative numbers get a leading '-'. 0 is "0". Raise ValueError if b is outside 2..36.""",
         visible=["assert to_base(255, 16) == 'ff'", "assert to_base(0, 2) == '0'"],
         hidden=["assert to_base(-10, 2) == '-1010'", "assert to_base(35, 36) == 'z'", "assert to_base(36, 36) == '10'",
                 "assert to_base(5, 10) == '5'", "assert to_base(1000, 7) == '2626'",
                 "assert _raises(ValueError, to_base, 5, 1)", "assert _raises(ValueError, to_base, 5, 37)"]),

    dict(id="rotate", entry="rotate_matrix", prompt="""\
Write `rotate_matrix(m: list[list[int]]) -> list[list[int]]` returning a NEW matrix rotated 90 degrees clockwise.
The matrix may be rectangular or empty. Do not mutate the input.""",
         visible=["assert rotate_matrix([[1,2],[3,4]]) == [[3,1],[4,2]]"],
         hidden=["assert rotate_matrix([]) == []", "assert rotate_matrix([[1,2,3]]) == [[1],[2],[3]]",
                 "assert rotate_matrix([[1],[2],[3]]) == [[3,2,1]]",
                 "assert rotate_matrix([[1,2,3],[4,5,6]]) == [[4,1],[5,2],[6,3]]",
                 "x = [[1,2],[3,4]]\nrotate_matrix(x)\nassert x == [[1,2],[3,4]]"]),

    dict(id="islands", entry="count_islands", prompt="""\
Write `count_islands(grid: list[str]) -> int`. Each string is a row of '1' (land) and '0' (water).
Count groups of land cells connected horizontally or vertically. Grids can be large (thousands of cells).""",
         visible=["assert count_islands(['11000','11000','00100','00011']) == 3"],
         hidden=["assert count_islands([]) == 0", "assert count_islands(['0']) == 0", "assert count_islands(['1']) == 1",
                 "assert count_islands(['101','010','101']) == 5", "assert count_islands(['111','101','111']) == 1",
                 "assert count_islands(['1' * 60] * 60) == 1"]),

    dict(id="runmedian", entry="RunningMedian", prompt="""\
Implement class `RunningMedian` with `add(x: int)` and `median() -> float`. median() returns the median of all
values added so far as a float (the mean of the two middle values for an even count) and raises ValueError if
nothing was added. It must stay fast for tens of thousands of values.""",
         visible=["m = RunningMedian(); m.add(1); m.add(3)\nassert m.median() == 2.0"],
         hidden=["m = RunningMedian()\nassert _raises(ValueError, m.median)",
                 "m = RunningMedian(); m.add(5); m.add(1); m.add(3)\nassert m.median() == 3",
                 "m = RunningMedian(); m.add(1)\nr = m.median()\nassert r == 1.0 and isinstance(r, float)",
                 "m = RunningMedian()\nfor v in [-5, -5, 2, 2]: m.add(v)\nassert m.median() == -1.5",
                 "m = RunningMedian()\nvals = [(i * 7919) % 10007 for i in range(20000)]\nfor v in vals: m.add(v)\ns = sorted(vals)\nassert m.median() == (s[9999] + s[10000]) / 2"]),

    dict(id="ranges", entry="summarize_ranges", prompt="""\
Write `summarize_ranges(nums: list[int]) -> list[str]` for a sorted list of unique integers, summarizing runs of
consecutive numbers as "a->b" and single numbers as "a".""",
         visible=["assert summarize_ranges([0,1,2,4,5,7]) == ['0->2','4->5','7']"],
         hidden=["assert summarize_ranges([]) == []", "assert summarize_ranges([1]) == ['1']",
                 "assert summarize_ranges([-3,-2,-1,1]) == ['-3->-1','1']", "assert summarize_ranges([1,3,5]) == ['1','3','5']",
                 "assert summarize_ranges([0,1]) == ['0->1']"]),

    dict(id="bowling", entry="bowling_score", prompt="""\
Write `bowling_score(rolls: list[int]) -> int` returning the total score of one complete, valid ten-pin bowling
game given as the list of pins knocked down per roll (standard strike/spare bonuses, including the bonus rolls of
the 10th frame).""",
         visible=["assert bowling_score([10] * 12) == 300", "assert bowling_score([0] * 20) == 0"],
         hidden=["assert bowling_score([5] * 21) == 150", "assert bowling_score([9, 0] * 10) == 90",
                 "assert bowling_score([10,7,3,9,0,10,0,8,8,2,0,6,10,10,10,8,1]) == 167",
                 "assert bowling_score([3,7,10,2,3] + [0] * 14) == 40",
                 "assert bowling_score([0] * 18 + [7,3,10]) == 20", "assert bowling_score([0] * 18 + [10,10,10]) == 30",
                 "assert bowling_score([0] * 18 + [10,3,4]) == 17"]),

    dict(id="humanize", entry="humanize_seconds", prompt="""\
Write `humanize_seconds(n: int) -> str`. Units: year (365 days), day, hour, minute, second. Show only non-zero units,
largest first, as "<count> <unit>" with a plural "s" when count != 1. Join one component as-is, two with " and ",
more as "a, b and c". 0 returns "now". Negative input raises ValueError.""",
         visible=["assert humanize_seconds(62) == '1 minute and 2 seconds'",
                  "assert humanize_seconds(3662) == '1 hour, 1 minute and 2 seconds'"],
         hidden=["assert humanize_seconds(0) == 'now'", "assert humanize_seconds(1) == '1 second'",
                 "assert humanize_seconds(120) == '2 minutes'", "assert humanize_seconds(86400 * 365 + 1) == '1 year and 1 second'",
                 "assert humanize_seconds(86400 * 2 + 60) == '2 days and 1 minute'",
                 "assert humanize_seconds(31536000 * 3 + 86400 * 4 + 3600) == '3 years, 4 days and 1 hour'",
                 "assert _raises(ValueError, humanize_seconds, -1)"]),

    dict(id="unique", entry="unique_preserve", prompt="""\
Write `unique_preserve(seq: list) -> list` removing duplicates (by ==) while keeping first occurrences in order.
Items may be unhashable (lists, dicts). It must be fast (roughly linear) for large lists of hashable items.""",
         visible=["assert unique_preserve([3,1,3,2,1]) == [3,1,2]"],
         hidden=["assert unique_preserve([]) == []", "assert unique_preserve([[1],[1],[2]]) == [[1],[2]]",
                 "assert unique_preserve([1, True, 1.0, 2]) == [1, 2]",
                 "assert unique_preserve(['a', {'x': 1}, 'a', {'x': 1}]) == ['a', {'x': 1}]",
                 "assert unique_preserve(list(range(30000)) * 2) == list(range(30000))"]),

    dict(id="rpn", entry="eval_rpn", prompt="""\
Write `eval_rpn(tokens: list[str]) -> int` evaluating Reverse Polish Notation with integer tokens (possibly negative,
like "-3") and operators + - * /. Division truncates toward zero. Raise ZeroDivisionError on division by zero and
ValueError for malformed input (unknown token, stack underflow, or not exactly one value left at the end).""",
         visible=["assert eval_rpn(['2','1','+','3','*']) == 9", "assert eval_rpn(['4','13','5','/','+']) == 6"],
         hidden=["assert eval_rpn(['-7','2','/']) == -3", "assert eval_rpn(['7','-2','/']) == -3",
                 "assert eval_rpn(['3']) == 3", "assert eval_rpn(['-3']) == -3",
                 "assert _raises(ValueError, eval_rpn, [])", "assert _raises(ValueError, eval_rpn, ['1','+'])",
                 "assert _raises(ValueError, eval_rpn, ['1','2'])", "assert _raises(ValueError, eval_rpn, ['1','2','^'])",
                 "assert _raises(ZeroDivisionError, eval_rpn, ['1','0','/'])"]),

    dict(id="versort", entry="sort_versions", prompt="""\
Write `sort_versions(vs: list[str]) -> list[str]` sorting dotted numeric versions ascending. Compare components
numerically; missing trailing components count as 0 (so "1" == "1.0"). The sort is stable for equal versions.""",
         visible=["assert sort_versions(['1.10','1.9','1.2']) == ['1.2','1.9','1.10']"],
         hidden=["assert sort_versions(['1.0','1']) == ['1.0','1']", "assert sort_versions(['1','1.0']) == ['1','1.0']",
                 "assert sort_versions(['2','1.0.1','1.0.0.1']) == ['1.0.0.1','1.0.1','2']", "assert sort_versions([]) == []",
                 "assert sort_versions(['0.10.0','0.9.99']) == ['0.9.99','0.10.0']"]),

    dict(id="vigenere", entry="vigenere_encrypt", prompt="""\
Write `vigenere_encrypt(text: str, key: str) -> str`. Shift each ASCII letter of text by the next key letter
(a/A = 0 ... z/Z = 25, key is case-insensitive), preserving the letter's case. Non-letters are copied unchanged and
do NOT consume a key letter. Raise ValueError if key is empty or contains non-letters.""",
         visible=["assert vigenere_encrypt('ATTACKATDAWN', 'LEMON') == 'LXFOPVEFRNHR'"],
         hidden=["assert vigenere_encrypt('attack at dawn', 'LEMON') == 'lxfopv ef rnhr'",
                 "assert vigenere_encrypt('Hello, World!', 'key') == 'Rijvs, Uyvjn!'",
                 "assert vigenere_encrypt('', 'abc') == ''",
                 "assert _raises(ValueError, vigenere_encrypt, 'x', '')",
                 "assert _raises(ValueError, vigenere_encrypt, 'x', 'a1')"]),

    dict(id="minwindow", entry="min_window", prompt="""\
Write `min_window(s: str, t: str) -> str` returning the shortest substring of s that contains every character of t
with at least the same multiplicity. If several are shortest, return the leftmost. Return "" if none exists or
t is empty.""",
         visible=["assert min_window('ADOBECODEBANC', 'ABC') == 'BANC'"],
         hidden=["assert min_window('a', 'a') == 'a'", "assert min_window('a', 'aa') == ''", "assert min_window('aa', 'aa') == 'aa'",
                 "assert min_window('abc', '') == ''", "assert min_window('ab', 'b') == 'b'", "assert min_window('bba', 'ab') == 'ba'",
                 "assert min_window('cabwefgewcwaefgcf', 'cae') == 'cwae'", "assert min_window('abab', 'ab') == 'ab'"]),

    dict(id="zigzag", entry="zigzag_convert", prompt="""\
Write `zigzag_convert(s: str, rows: int) -> str`: write s in a zigzag pattern on `rows` rows (down, then diagonally
up, repeat) and read it row by row. rows >= 1.""",
         visible=["assert zigzag_convert('PAYPALISHIRING', 3) == 'PAHNAPLSIIGYIR'"],
         hidden=["assert zigzag_convert('PAYPALISHIRING', 4) == 'PINALSIGYAHRPI'", "assert zigzag_convert('AB', 1) == 'AB'",
                 "assert zigzag_convert('', 3) == ''", "assert zigzag_convert('ABC', 5) == 'ABC'",
                 "assert zigzag_convert('ABCD', 2) == 'ACBD'"]),

    dict(id="histogram", entry="largest_rectangle", prompt="""\
Write `largest_rectangle(heights: list[int]) -> int` returning the area of the largest rectangle in a histogram of
bars with width 1. Inputs can have tens of thousands of bars, so it must be efficient.""",
         visible=["assert largest_rectangle([2,1,5,6,2,3]) == 10"],
         hidden=["assert largest_rectangle([]) == 0", "assert largest_rectangle([0]) == 0", "assert largest_rectangle([2,4]) == 4",
                 "assert largest_rectangle([1] * 20000) == 20000", "assert largest_rectangle([6,2,5,4,5,1,6]) == 12",
                 "assert largest_rectangle([5,4,3,2,1]) == 9"]),

    dict(id="ipv4", entry="valid_ipv4", prompt="""\
Write `valid_ipv4(s: str) -> bool`: exactly four parts separated by '.', each part is 1-3 ASCII digits (0-9 only)
with value 0-255 and no leading zeros (except "0" itself). No spaces, signs or other characters.""",
         visible=["assert valid_ipv4('192.168.0.1') is True", "assert valid_ipv4('256.1.1.1') is False"],
         hidden=["assert valid_ipv4('0.0.0.0') is True", "assert valid_ipv4('01.1.1.1') is False",
                 "assert valid_ipv4('1.1.1') is False", "assert valid_ipv4('1.1.1.1.') is False",
                 "assert valid_ipv4('1..1.1') is False", "assert valid_ipv4(' 1.1.1.1') is False",
                 "assert valid_ipv4('1.1.1.+1') is False", "assert valid_ipv4('255.255.255.255') is True",
                 "assert valid_ipv4('1.1.1.1.1') is False", "assert valid_ipv4('١.1.1.1') is False"]),

    dict(id="getpath", entry="get_path", prompt="""\
Write `get_path(obj, path: str)` resolving a path like "a.b[0].c" in nested dicts/lists. Dict keys are identifiers
([A-Za-z_][A-Za-z0-9_]*), list indexes are non-negative integers in brackets ("[1]", "a[0][1]"). An empty path returns
obj itself. Raise KeyError if any step cannot be resolved (missing key, index out of range, wrong container type,
or malformed path such as a negative index).""",
         visible=["assert get_path({'a': {'b': [{'c': 5}]}}, 'a.b[0].c') == 5"],
         hidden=["assert get_path([10, 20], '[1]') == 20", "assert get_path({'a': [[1, 2], [3]]}, 'a[0][1]') == 2",
                 "assert get_path({'a': 1}, '') == {'a': 1}", "assert get_path({'x_1': {'y': None}}, 'x_1.y') is None",
                 "assert _raises(KeyError, get_path, {'a': 1}, 'b')", "assert _raises(KeyError, get_path, {'a': [1]}, 'a[1]')",
                 "assert _raises(KeyError, get_path, {'a': 1}, 'a.b')", "assert _raises(KeyError, get_path, {'a': [1]}, 'a.0')",
                 "assert _raises(KeyError, get_path, {'a': [1, 2]}, 'a[-1]')"]),

    dict(id="freeslots", entry="free_slots", prompt="""\
Write `free_slots(busy: list[list[int]], start: int, end: int) -> list[list[int]]`. busy holds half-open intervals
[s, e) that may be unsorted, overlapping, touching, empty, or extend outside [start, end). Return the free gaps inside
[start, end) as sorted [s, e] pairs with positive length.""",
         visible=["assert free_slots([[9,10],[12,13]], 8, 17) == [[8,9],[10,12],[13,17]]"],
         hidden=["assert free_slots([], 8, 17) == [[8,17]]", "assert free_slots([[7,18]], 8, 17) == []",
                 "assert free_slots([[9,11],[10,12],[12,13]], 8, 17) == [[8,9],[13,17]]",
                 "assert free_slots([[13,14],[9,10]], 9, 14) == [[10,13]]",
                 "assert free_slots([[5,8],[17,20]], 8, 17) == [[8,17]]", "assert free_slots([[8,8]], 8, 10) == [[8,10]]"]),
    dict(id="query", entry="parse_query", prompt="""\
Write `parse_query(qs: str) -> dict[str, list[str]]` parsing a URL query string. Strip one leading '?'. Split on '&'
and skip empty pieces. Split each piece on the FIRST '='; a piece without '=' has value "". Decode '+' as a space and
%XX percent-escapes (UTF-8) in both keys and values. Values for a repeated key are collected in order.
Blank values must be kept.""",
         visible=["assert parse_query('a=1&b=2&a=3') == {'a': ['1', '3'], 'b': ['2']}"],
         hidden=["assert parse_query('') == {}", "assert parse_query('?x=1') == {'x': ['1']}",
                 "assert parse_query('flag&x=') == {'flag': [''], 'x': ['']}",
                 "assert parse_query('q=hello+world%21') == {'q': ['hello world!']}",
                 "assert parse_query('a=b=c') == {'a': ['b=c']}", "assert parse_query('&&a=1&') == {'a': ['1']}",
                 "assert parse_query('%E4%BD%A0=%E5%A5%BD') == {'你': ['好']}",
                 "assert parse_query('a%2Bb=1') == {'a+b': ['1']}"]),
]

# 留出集：只用于最终评估，进化过程中 meta 模型永远看不到这些题
HELDOUT_IDS = {"duration", "wrap", "path", "words", "balanced", "cron", "bytes", "flatten",
               "camel", "addmonths", "bowling", "humanize", "rpn", "ipv4", "freeslots", "getpath"}

DEV = [t for t in TASKS if t["id"] not in HELDOUT_IDS]
HELDOUT = [t for t in TASKS if t["id"] in HELDOUT_IDS]
