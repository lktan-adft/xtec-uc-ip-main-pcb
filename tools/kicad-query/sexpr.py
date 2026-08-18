"""Minimal S-expression parser for KiCad's .kicad_pcb / .kicad_sch files.

Stdlib-only, single-pass tokenizer + recursive-descent parser. KiCad's file
format is plain S-expressions (`(token arg1 arg2 (nested ...) ...)`), so a
generic parser here is more robust than regex over a 15+ MB file with
arbitrarily nested, multi-line blocks -- and it's what every other tool in
this repo's toolbox (kicad-cli itself) treats the format as.

Returns nested Python lists: symbols become plain strings, quoted strings
have their escapes resolved and stay strings (indistinguishable from
symbols once parsed -- callers that care about the distinction should check
the source text, not the parsed tree). Numbers are left as strings too;
convert at the call site if needed.
"""
import re

_TOKEN_RE = re.compile(
    r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))'
)


def tokenize(text):
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN_RE.match(text, pos)
        if not m:
            pos += 1
            continue
        pos = m.end()
        if m.group(1):
            yield "("
        elif m.group(2):
            yield ")"
        elif m.group(3) is not None:
            yield ("str", m.group(3).replace('\\"', '"').replace("\\\\", "\\"))
        elif m.group(4):
            yield ("sym", m.group(4))


def parse(text):
    """Parse the whole file, returning the single top-level expression."""
    tokens = tokenize(text)
    stack = []
    current = None
    for tok in tokens:
        if tok == "(":
            new_list = []
            if current is not None:
                stack.append(current)
            current = new_list
        elif tok == ")":
            finished = current
            if stack:
                current = stack.pop()
                current.append(finished)
            else:
                return finished
        else:
            _, value = tok
            if current is None:
                return value
            current.append(value)
    return current


def find_all(node, tag):
    """Yield every direct-child list of `node` whose head symbol == tag."""
    if not isinstance(node, list):
        return
    for child in node:
        if isinstance(child, list) and child and child[0] == tag:
            yield child


def find_first(node, tag):
    return next(find_all(node, tag), None)


def text_of(node):
    """Unwrap a 1-arg node like `(reference "U6")` to just "U6"."""
    if isinstance(node, list) and len(node) >= 2:
        return node[1]
    return None
