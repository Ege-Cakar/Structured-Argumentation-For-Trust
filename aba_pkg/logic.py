from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, Any, Callable, Dict, Set

from .baba import Literal, LiteralType

# ---------- 1. Structured modal formula ----------
@dataclass(frozen=True)
class Formula:
    mods: Tuple[str, ...]   # e.g. ('B','alice') or ('O',)
    atom: str               # base proposition identifier
    neg: bool = False       # syntactic negation flag
    meta: Any = field(default=None, compare=False)  # optional payload (e.g. original natural language text)

    def key(self) -> str:
        """Canonical engine key."""
        prefix = ''.join(f'{m}:' for m in self.mods)
        return f"{'¬' if self.neg else ''}{prefix}{self.atom}"

# ---------- 2. Default contrary ----------
def flip_neg(f: Formula) -> Formula:
    return Formula(f.mods, f.atom, not f.neg, f.meta)

# ---------- 3. Tiny adapter to interact with the B_ABA engine ----------
@dataclass
class ModalAdapter:
    contrary_fn: Callable[[Formula], Formula] = flip_neg

    def to_literal(self, f: Formula, lit_type: LiteralType = LiteralType.ASSUMPTION) -> Literal:
        return Literal(f.key(), lit_type, payload=f)

    def contrary_literal(self, lit: Literal) -> Literal:
        f = self.parse(lit.key)
        cf = self.contrary_fn(f)
        return Literal(cf.key(), lit.type, payload=cf)

    # Very lightweight parser for our canonical key format
    def parse(self, key: str) -> Formula:
        neg = key.startswith('¬')
        core = key[1:] if neg else key
        parts = core.split(':')
        if len(parts) == 1:
            return Formula((), parts[0], neg)
        *mods, atom = parts
        return Formula(tuple(mods), atom, neg)

# ---------- 4. Helper to build a contrary map for the framework ----------
def build_contrary_map(assumptions: Set[Literal], adapter: ModalAdapter) -> Dict[Literal, Literal]:
    out: Dict[Literal, Literal] = {}
    for lit in assumptions:
        out[lit] = adapter.contrary_literal(lit)
    return out