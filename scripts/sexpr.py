"""Minimal s-expression reader for KiCad files."""
import re

_TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


def parse(text):
    stack, cur = [], []
    for tok in _TOKEN.findall(text):
        if tok == "(":
            stack.append(cur); cur = []
        elif tok == ")":
            done = cur; cur = stack.pop(); cur.append(done)
        else:
            cur.append(tok[1:-1] if tok.startswith('"') else tok)
    return cur[0]


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def val(node, key):
    f = find(node, key)
    return f[0][1] if f else None
