"""
spreadsheet_engine.py — Moteur de tableur (type Excel) sans dépendance.
Grille de cellules + évaluation de formules ('=...') via un parseur
récursif-descendant propre (pas de juggling de regex).

Supporte : littéraux numériques/texte, références (A1), plages (A1:B3),
opérateurs + - * / ^, parenthèses, comparaisons (> < >= <= = <>),
et un jeu de fonctions financières/statistiques.

Logique pure : aucun import pygame. Testable seule.
"""
import math


# ---------------------------------------------------------------------------
# Fonctions intégrées. Reçoivent une liste d'arguments déjà évalués.
# Les plages sont passées comme listes ; on les aplatit au besoin.
# ---------------------------------------------------------------------------
def _flatten(args):
    out = []
    for a in args:
        if isinstance(a, (list, tuple)):
            out.extend(_flatten(a))
        else:
            out.append(a)
    return out


def _nums(args):
    vals = []
    for v in _flatten(args):
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            continue
    return vals


def _stdev(vals):
    if len(vals) < 2:
        return 0.0
    m = sum(vals) / len(vals)
    return math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))


def _npv(args):
    flat = _nums(args)
    rate = flat[0]
    flows = flat[1:]
    return sum(cf / ((1 + rate) ** (t + 1)) for t, cf in enumerate(flows))


def _irr(args):
    flows = _nums(args)
    rate = 0.1
    for _ in range(200):
        npv = sum(cf / ((1 + rate) ** t) for t, cf in enumerate(flows))
        d = sum(-t * cf / ((1 + rate) ** (t + 1)) for t, cf in enumerate(flows))
        if abs(d) < 1e-12:
            break
        new = rate - npv / d
        if abs(new - rate) < 1e-9:
            return new
        rate = new
    return rate


def _pmt(args):
    f = _nums(args)
    rate, nper, pv = f[0], f[1], f[2]
    if rate == 0:
        return -pv / nper
    return -pv * rate * (1 + rate) ** nper / ((1 + rate) ** nper - 1)


FUNCTIONS = {
    "SUM":     lambda a: sum(_nums(a)),
    "AVERAGE": lambda a: (sum(_nums(a)) / len(_nums(a))) if _nums(a) else 0.0,
    "MEAN":    lambda a: (sum(_nums(a)) / len(_nums(a))) if _nums(a) else 0.0,
    "MIN":     lambda a: min(_nums(a)) if _nums(a) else 0.0,
    "MAX":     lambda a: max(_nums(a)) if _nums(a) else 0.0,
    "COUNT":   lambda a: float(len(_nums(a))),
    "ABS":     lambda a: abs(_nums(a)[0]) if _nums(a) else 0.0,
    "SQRT":    lambda a: math.sqrt(_nums(a)[0]) if _nums(a) else 0.0,
    "POWER":   lambda a: _nums(a)[0] ** _nums(a)[1],
    "EXP":     lambda a: math.exp(_nums(a)[0]),
    "LN":      lambda a: math.log(_nums(a)[0]),
    "LOG":     lambda a: math.log(_nums(a)[0], _nums(a)[1]) if len(_nums(a)) > 1 else math.log10(_nums(a)[0]),
    "ROUND":   lambda a: round(_nums(a)[0], int(_nums(a)[1]) if len(_nums(a)) > 1 else 0),
    "STDEV":   lambda a: _stdev(_nums(a)),
    "VAR":     lambda a: _stdev(_nums(a)) ** 2,
    "NPV":     _npv,
    "IRR":     _irr,
    "PMT":     _pmt,
    "IF":      lambda a: a[1] if a[0] else (a[2] if len(a) > 2 else 0.0),
}


# ---------------------------------------------------------------------------
# Conversion colonnes
# ---------------------------------------------------------------------------
def col_to_idx(col):
    idx = 0
    for ch in col:
        idx = idx * 26 + (ord(ch) - ord('A') + 1)
    return idx - 1


def idx_to_col(idx):
    s = ""
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        s = chr(ord('A') + rem) + s
    return s


# ---------------------------------------------------------------------------
# Tokeniseur
# ---------------------------------------------------------------------------
class Tok:
    NUM, REF, FUNC, OP, LP, RP, COMMA, COLON, STR = range(9)

    def __init__(self, kind, val):
        self.kind = kind
        self.val = val

    def __repr__(self):
        return f"Tok({self.kind},{self.val!r})"


def tokenize(s):
    toks = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c == '"':
            j = i + 1
            while j < n and s[j] != '"':
                j += 1
            toks.append(Tok(Tok.STR, s[i + 1:j]))
            i = j + 1
            continue
        if c.isdigit() or (c == '.' and i + 1 < n and s[i + 1].isdigit()):
            j = i
            while j < n and (s[j].isdigit() or s[j] == '.'):
                j += 1
            # notation scientifique
            if j < n and s[j] in 'eE':
                j += 1
                if j < n and s[j] in '+-':
                    j += 1
                while j < n and s[j].isdigit():
                    j += 1
            toks.append(Tok(Tok.NUM, float(s[i:j])))
            i = j
            continue
        if c.isalpha():
            j = i
            while j < n and s[j].isalnum():
                j += 1
            word = s[i:j]
            # référence cellule = lettres puis chiffres (ex A1, AB12)
            k = 0
            while k < len(word) and word[k].isalpha():
                k += 1
            if k < len(word) and word[k:].isdigit():
                toks.append(Tok(Tok.REF, word.upper()))
            else:
                toks.append(Tok(Tok.FUNC, word.upper()))
            i = j
            continue
        if c in '+-*/^':
            toks.append(Tok(Tok.OP, c))
            i += 1
            continue
        if c in '<>=':
            # opérateurs de comparaison (>=, <=, <>, >, <, =)
            two = s[i:i + 2]
            if two in ('>=', '<=', '<>'):
                toks.append(Tok(Tok.OP, two))
                i += 2
            else:
                toks.append(Tok(Tok.OP, c))
                i += 1
            continue
        if c == '(':
            toks.append(Tok(Tok.LP, c)); i += 1; continue
        if c == ')':
            toks.append(Tok(Tok.RP, c)); i += 1; continue
        if c == ',':
            toks.append(Tok(Tok.COMMA, c)); i += 1; continue
        if c == ':':
            toks.append(Tok(Tok.COLON, c)); i += 1; continue
        raise ValueError(f"Caractère inattendu : {c!r}")
    return toks


# ---------------------------------------------------------------------------
# Parseur récursif-descendant -> évaluation directe
#   expr    := compare
#   compare := add ((> < >= <= = <>) add)*
#   add     := mul (('+'|'-') mul)*
#   mul     := pow (('*'|'/') pow)*
#   pow     := unary ('^' unary)*
#   unary   := ('-'|'+') unary | atom
#   atom    := NUM | STR | REF [':' REF] | FUNC '(' args ')' | '(' expr ')'
# ---------------------------------------------------------------------------
class Parser:
    def __init__(self, toks, sheet):
        self.toks = toks
        self.pos = 0
        self.sheet = sheet

    def peek(self):
        return self.toks[self.pos] if self.pos < len(self.toks) else None

    def next(self):
        t = self.toks[self.pos]
        self.pos += 1
        return t

    def expect(self, kind):
        t = self.next()
        if t.kind != kind:
            raise ValueError("Syntaxe invalide")
        return t

    def parse(self):
        v = self.compare()
        if self.pos != len(self.toks):
            raise ValueError("Tokens en trop")
        return v

    def compare(self):
        left = self.add()
        t = self.peek()
        while t and t.kind == Tok.OP and t.val in ('>', '<', '>=', '<=', '=', '<>'):
            self.next()
            right = self.add()
            op = t.val
            if op == '>':  left = left > right
            elif op == '<': left = left < right
            elif op == '>=': left = left >= right
            elif op == '<=': left = left <= right
            elif op == '=': left = left == right
            elif op == '<>': left = left != right
            t = self.peek()
        return left

    def add(self):
        left = self.mul()
        t = self.peek()
        while t and t.kind == Tok.OP and t.val in ('+', '-'):
            self.next()
            right = self.mul()
            left = (left + right) if t.val == '+' else (left - right)
            t = self.peek()
        return left

    def mul(self):
        left = self.powr()
        t = self.peek()
        while t and t.kind == Tok.OP and t.val in ('*', '/'):
            self.next()
            right = self.powr()
            left = (left * right) if t.val == '*' else (left / right)
            t = self.peek()
        return left

    def powr(self):
        left = self.unary()
        t = self.peek()
        while t and t.kind == Tok.OP and t.val == '^':
            self.next()
            right = self.unary()
            left = left ** right
            t = self.peek()
        return left

    def unary(self):
        t = self.peek()
        if t and t.kind == Tok.OP and t.val in ('+', '-'):
            self.next()
            v = self.unary()
            return -v if t.val == '-' else v
        return self.atom()

    def atom(self):
        t = self.next()
        if t.kind == Tok.NUM:
            return t.val
        if t.kind == Tok.STR:
            return t.val
        if t.kind == Tok.LP:
            v = self.compare()
            self.expect(Tok.RP)
            return v
        if t.kind == Tok.REF:
            # plage ?
            nxt = self.peek()
            if nxt and nxt.kind == Tok.COLON:
                self.next()
                end = self.expect(Tok.REF)
                return self._range_values(t.val, end.val)
            return self._num(self.sheet.get_value(t.val))
        if t.kind == Tok.FUNC:
            self.expect(Tok.LP)
            args = self.arglist()
            self.expect(Tok.RP)
            fn = FUNCTIONS.get(t.val)
            if not fn:
                raise ValueError(f"Fonction inconnue : {t.val}")
            return fn(args)
        raise ValueError("Atome inattendu")

    def arglist(self):
        args = []
        if self.peek() and self.peek().kind == Tok.RP:
            return args
        args.append(self.compare())
        while self.peek() and self.peek().kind == Tok.COMMA:
            self.next()
            args.append(self.compare())
        return args

    def _num(self, v):
        if isinstance(v, bool):
            return v
        try:
            return float(v)
        except (TypeError, ValueError):
            return v  # texte ou marqueur d'erreur

    def _range_values(self, c1, c2):
        return [self._num(self.sheet.get_value(r))
                for r in self.sheet.expand_range(c1, c2)]


# ---------------------------------------------------------------------------
# Tableur
# ---------------------------------------------------------------------------
class Spreadsheet:
    def __init__(self, rows=20, cols=8):
        self.rows = rows
        self.cols = cols
        self.cells = {}
        self._cache = {}
        self._evaluating = set()

    def set(self, ref, raw):
        self.cells[ref] = raw
        self._cache.clear()

    def get_raw(self, ref):
        return self.cells.get(ref, "")

    def get_value(self, ref):
        if ref in self._cache:
            return self._cache[ref]
        if ref in self._evaluating:
            return "#CYCLE"
        raw = self.cells.get(ref, "")
        if raw is None or raw == "":
            return 0.0
        self._evaluating.add(ref)
        try:
            val = self._eval_raw(raw)
        except Exception:
            val = "#ERR"
        finally:
            self._evaluating.discard(ref)
        self._cache[ref] = val
        return val

    def _eval_raw(self, raw):
        raw = str(raw).strip()
        if not raw.startswith("="):
            try:
                return float(raw)
            except ValueError:
                return raw
        toks = tokenize(raw[1:])
        return Parser(toks, self).parse()

    def expand_range(self, c1, c2):
        def split(ref):
            i = 0
            while i < len(ref) and ref[i].isalpha():
                i += 1
            return col_to_idx(ref[:i]), int(ref[i:])
        col1, row1 = split(c1)
        col2, row2 = split(c2)
        refs = []
        for c in range(min(col1, col2), max(col1, col2) + 1):
            for r in range(min(row1, row2), max(row1, row2) + 1):
                refs.append(f"{idx_to_col(c)}{r}")
        return refs

    def to_dict(self):
        return dict(self.cells)

    def load_dict(self, d):
        self.cells = dict(d)
        self._cache.clear()
