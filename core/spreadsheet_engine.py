"""
spreadsheet_engine.py — Moteur de tableur (type Excel) sans dépendance.
Grille de cellules + évaluation de formules ('=...') via un parseur
récursif-descendant propre (pas de juggling de regex).

Supporte : littéraux numériques/texte, références (A1, avec ancres absolues
$A$1/$A1/A$1 façon Excel), plages (A1:B3), opérateurs + - * / ^, parenthèses,
comparaisons (> < >= <= = <>), et un jeu de fonctions financières/statistiques.

Logique pure : aucun import pygame. Testable seule.
"""
import math
import re


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


def _pv(args):
    f = _nums(args)
    rate, nper, pmt = f[0], f[1], f[2]
    if rate == 0:
        return -pmt * nper
    return -pmt * (1 - (1 + rate) ** (-nper)) / rate


def _fv(args):
    f = _nums(args)
    rate, nper, pmt = f[0], f[1], f[2]
    if rate == 0:
        return -pmt * nper
    return -pmt * (((1 + rate) ** nper - 1) / rate)


def _median(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _correl(args):
    """CORREL(plageX, plageY) — corrélation de Pearson entre deux plages de
    même longueur (usage classique finance : deux séries de rendements)."""
    if len(args) < 2:
        return 0.0
    xs = _nums([args[0]])
    ys = _nums([args[1]])
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    xs, ys = xs[:n], ys[:n]
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return cov / (sx * sy) if sx and sy else 0.0


FUNCTIONS = {
    "SUM":     lambda a: sum(_nums(a)),
    "AVERAGE": lambda a: (sum(_nums(a)) / len(_nums(a))) if _nums(a) else 0.0,
    "MEAN":    lambda a: (sum(_nums(a)) / len(_nums(a))) if _nums(a) else 0.0,
    "MEDIAN":  lambda a: _median(_nums(a)),
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
    "CORREL":  _correl,
    "NPV":     _npv,
    "IRR":     _irr,
    "PMT":     _pmt,
    "PV":      _pv,
    "FV":      _fv,
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
# Décalage de références (collage relatif façon Excel)
# ---------------------------------------------------------------------------
_REF_RE = re.compile(r'(\$?)([A-Za-z]+)(\$?)([0-9]+)')


def shift_formula(raw, dr, dc):
    """Réécrit les références d'une formule décalée de (`dr` lignes,
    `dc` colonnes) — le comportement d'Excel au collage : `=B1*2` copié une
    ligne plus bas devient `=B2*2`. Les ancres `$` bloquent le décalage
    ($A$1 ne bouge jamais, $A1 fige la colonne, A$1 fige la ligne). Une
    référence décalée hors grille devient `#REF` (la cellule affichera une
    erreur, comme Excel). Les non-formules et les textes entre guillemets
    sont laissés intacts."""
    s = str(raw)
    if not s.startswith("="):
        return s
    out, i, n = [], 0, len(s)
    while i < n:
        ch = s[i]
        if ch == '"':                      # littéral texte : ne pas toucher
            j = s.find('"', i + 1)
            j = n - 1 if j < 0 else j
            out.append(s[i:j + 1])
            i = j + 1
            continue
        m = _REF_RE.match(s, i)
        # pas une référence si collée à un identifiant plus long (ex. « X1 »
        # au milieu de « MAX1 ») ou suivie de lettres
        if m and not (i > 0 and (s[i - 1].isalnum() or s[i - 1] == '$')):
            end = m.end()
            if end < n and s[end].isalpha():
                out.append(ch)
                i += 1
                continue
            # nom de fonction du type LOG10( : pas une référence
            k = end
            while k < n and s[k].isspace():
                k += 1
            if k < n and s[k] == '(':
                out.append(s[i:end])
                i = end
                continue
            dol_c, col, dol_r, row = m.groups()
            ci = col_to_idx(col.upper()) + (0 if dol_c else dc)
            ri = int(row) + (0 if dol_r else dr)
            if ci < 0 or ri < 1:
                out.append("#REF")
            else:
                out.append(f"{dol_c}{idx_to_col(ci)}{dol_r}{ri}")
            i = end
            continue
        out.append(ch)
        i += 1
    return "".join(out)


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
        if c == '$' or c.isalpha():
            # référence ANCRÉE ($A$1, $A1, A$1) : les '$' sont des marqueurs
            # d'ancrage pour le collage relatif (shift_formula) — l'évaluation
            # les ignore (même valeur que A1).
            j = i + (1 if c == '$' else 0)
            k = j
            while k < n and s[k].isalpha():
                k += 1
            letters = s[j:k]
            m = k + (1 if k < n and s[k] == '$' else 0)
            d = m
            while d < n and s[d].isdigit():
                d += 1
            if c == '$' or m > k:
                if letters and d > m:
                    toks.append(Tok(Tok.REF, (letters + s[m:d]).upper()))
                    i = d
                    continue
                raise ValueError("Référence invalide après '$'")
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
            if t.val == "VLOOKUP":
                return self._vlookup()
            args = self.arglist()
            self.expect(Tok.RP)
            fn = FUNCTIONS.get(t.val)
            if fn:
                return fn(args)
            # fonctions EXTERNES (données vivantes injectées par l'app, ex.
            # PRICE/INDEX/FX/NETWORTH — cf. apps/app_sheet.py). Le moteur reste
            # pur : il ne connaît pas le marché, il délègue au résolveur.
            ext = getattr(self.sheet, "external", None)
            if ext is not None:
                val = ext(t.val, args)
                if val is not None:
                    return val
            raise ValueError(f"Fonction inconnue : {t.val}")
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

    def _range_grid(self, c1, c2):
        """Comme `_range_values` mais préserve la forme (liste de LIGNES, chaque
        ligne étant la liste des valeurs de ses colonnes) — nécessaire pour
        VLOOKUP (recherche sur la 1re colonne, retourne une autre colonne de la
        MÊME ligne), impossible à partir d'une liste aplatie."""
        def split(ref):
            i = 0
            while i < len(ref) and ref[i].isalpha():
                i += 1
            return col_to_idx(ref[:i]), int(ref[i:])
        col1, row1 = split(c1)
        col2, row2 = split(c2)
        cmin, cmax = min(col1, col2), max(col1, col2)
        rmin, rmax = min(row1, row2), max(row1, row2)
        grid = []
        for r in range(rmin, rmax + 1):
            grid.append([self._num(self.sheet.get_value(f"{idx_to_col(c)}{r}"))
                        for c in range(cmin, cmax + 1)])
        return grid

    def _vlookup(self):
        """VLOOKUP(valeur_recherchée, plage, index_colonne) — cherche
        `valeur_recherchée` dans la 1re colonne de `plage` (correspondance
        EXACTE) et renvoie la valeur de la colonne `index_colonne` (1 = la
        1re colonne elle-même) de la ligne trouvée. `#N/A` si non trouvée."""
        search = self.compare()
        self.expect(Tok.COMMA)
        start = self.expect(Tok.REF)
        self.expect(Tok.COLON)
        end = self.expect(Tok.REF)
        self.expect(Tok.COMMA)
        col_idx = int(self.compare())
        # 4e argument optionnel (correspondance approx. façon Excel) accepté
        # mais ignoré : seule la correspondance EXACTE est supportée ici,
        # suffisante pour l'usage courant (recherche de ticker/étiquette).
        if self.peek() and self.peek().kind == Tok.COMMA:
            self.next()
            self.compare()
        self.expect(Tok.RP)
        grid = self._range_grid(start.val, end.val)
        for row in grid:
            if not row:
                continue
            if row[0] == search:
                if 1 <= col_idx <= len(row):
                    return row[col_idx - 1]
                return "#REF"
        return "#N/A"


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
        # résolveur de fonctions EXTERNES optionnel : callable(name, args)->valeur
        # (ou None si la fonction n'est pas reconnue). Injecté par l'app pour
        # les données vivantes (PRICE/INDEX/FX…) — le moteur reste pur.
        self.external = None

    def invalidate(self):
        """Vide le cache d'évaluation — à appeler quand une source EXTERNE
        (marché) a changé sans qu'aucune cellule n'ait été éditée, pour que les
        formules à données vivantes (PRICE/INDEX…) se recalculent."""
        self._cache.clear()

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
