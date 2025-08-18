from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Set, Any, Tuple, Callable, Iterable, List
from enum import Enum
from collections import Counter
from itertools import combinations
from copy import deepcopy
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import lru_cache
import multiprocessing as mp
from tqdm import tqdm
from itertools import cycle
import threading
import time
import re
from pysat.solvers import Glucose4, Minisat22
from pysat.formula import CNF
from pysat.card import CardEnc


# Notes:
# Δ attacks β iff there exists a subset Δ′ ⊆ Δ such that Δ′ ⊢ ¯β (a deduction of the contrary of β). Since in deductions 
# you can utilize rules whos bodies are in ∆, anything that can be reached from ∆' can be utilized in the derivation of ¯β
# Thus, checking attackers among Cl(Δ) is equivalent to searching all derivations.

class Spinner:
    """A simple spinner to show the program is working."""
    def __init__(self, message="Working"):
        self.spinner = cycle(['◐', '◓', '◑', '◒'])
        self.delay = 0.1
        self.busy = False
        self.spinner_thread = None
        self.message = message
        self.stats = {}
        self.stats_lock = threading.Lock()
        
    def update_stats(self, **kwargs):
        """Update statistics to display."""
        with self.stats_lock:
            self.stats.update(kwargs)
    
    def _spin(self):
        """The actual spinning function."""
        import sys
        while self.busy:
            with self.stats_lock:
                stats_str = " | ".join(f"{k}: {v}" for k, v in self.stats.items())
            
            spin_char = next(self.spinner)
            display = f"\r{spin_char} {self.message}"
            if stats_str:
                display += f" | {stats_str}"
            
            # Add padding to clear previous text
            display = f"{display:<100}"
            
            # Write directly to stdout with flush
            sys.stdout.write(display)
            sys.stdout.flush()
            time.sleep(self.delay)
    
    def start(self):
        """Start the spinner."""
        self.busy = True
        self.spinner_thread = threading.Thread(target=self._spin)
        self.spinner_thread.start()
    
    def stop(self, final_message=None):
        """Stop the spinner."""
        self.busy = False
        if self.spinner_thread:
            self.spinner_thread.join()
        
        # Clear the line
        import sys
        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.flush()
        
        if final_message:
            print(final_message)

class LiteralType(Enum):
    ASSUMPTION = "assumption"
    FACT = "fact"

# ---------- Dataclasses ----------
@dataclass(frozen=True)
class Literal:
    key: str
    type: LiteralType
    payload: Any = field(default=None, compare=False)

    def __hash__(self) -> int:
        return hash(self.key)

    def __str__(self) -> str:
        return self.key

    def __repr__(self) -> str:
        return f"Literal(key={self.key}, type={self.type}, payload={self.payload})"

# ---------- Rule ----------
@dataclass(frozen=True)
class Rule:
    """Bipolar rule: head ← body   (body ∈ A; head ∈ A ∪ ¯A)."""
    head: Literal
    body: Literal

    def __post_init__(self):
        if not isinstance(self.head, Literal) or not isinstance(self.body, Literal):
            raise TypeError("Rule.head and Rule.body must be Literal instances.")

# ---------- Framework ----------
@dataclass
class BipolarABA:
    assumptions: Set[Literal]
    contrary: Dict[Literal, Literal]         # α -> ¯α
    rules: Set[Rule]

    _support_from: Dict[Literal, Set[Literal]] = field(init=False, default_factory=dict)
    _attack_from:  Dict[Literal, Set[Literal]] = field(init=False, default_factory=dict)
    _inv_contrary: Dict[Literal, Literal] = field(init=False, default_factory=dict)

    def __post_init__(self):
        self._validate_core()
        self._index_rules()
        self._build_matrices()
        self._closure_cache = {}

    # --- validation ---
    def _validate_core(self) -> None:
        if not isinstance(self.assumptions, set) or not all(isinstance(a, Literal) for a in self.assumptions):
            raise TypeError("assumptions must be a set[Literal]")

        # contrary total on A
        missing = self.assumptions - self.contrary.keys()
        if missing:
            raise ValueError(f"Contrary missing for assumptions: {{ {', '.join(m.key for m in missing)} }}")
        vals = list(self.contrary.values())
        dups = {v.key for v, c in Counter(vals).items() if c > 1}
        if dups:
            raise ValueError(f"Multiple assumptions share the same contrary: {dups}")

        all_contraries = set(self.contrary.values())
        for r in self.rules:
            if r.body not in self.assumptions:
                raise ValueError(f"Rule body {r.body} is not an assumption")
            if (r.head not in self.assumptions) and (r.head not in all_contraries):
                raise ValueError(f"Rule head {r.head} is neither an assumption nor a known contrary")

    # --- indexing ---
    def _index_rules(self) -> None:
        self._support_from = {a: set() for a in self.assumptions}
        self._attack_from  = {a: set() for a in self.assumptions}

        self._inv_contrary = {v: k for k, v in self.contrary.items()}  # ¯β -> β

        for r in self.rules:
            if r.head in self.assumptions:          # support rule β ← α
                self._support_from[r.body].add(r.head)
            else:                                    # attack rule ¯β ← α
                attacked = self._inv_contrary[r.head]
                self._attack_from[r.body].add(attacked)

    def _build_matrices(self) -> None:
        """Build adjacency matrices for faster computation."""
        # Create assumption index mapping
        self._assumption_list = list(self.assumptions)
        self._assumption_idx = {a: i for i, a in enumerate(self._assumption_list)}
        n = len(self._assumption_list)
        
        # Support matrix: support[i,j] = 1 if i supports j
        self._support_matrix = np.zeros((n, n), dtype=bool)
        for i, a in enumerate(self._assumption_list):
            for supported in self._support_from.get(a, set()):
                j = self._assumption_idx[supported]
                self._support_matrix[i, j] = True
        
        # Attack matrix: attack[i,j] = 1 if i attacks j
        self._attack_matrix = np.zeros((n, n), dtype=bool)
        for i, a in enumerate(self._assumption_list):
            for attacked in self._attack_from.get(a, set()):
                j = self._assumption_idx[attacked]
                self._attack_matrix[i, j] = True
        
        # Precompute transitive closure of support (for fast closure computation)
        self._support_closure = self._compute_transitive_closure(self._support_matrix)

    def _compute_transitive_closure(self, matrix: np.ndarray) -> np.ndarray:
        """Compute transitive closure using Warshall's algorithm."""
        n = matrix.shape[0]
        closure = matrix.copy()
        np.fill_diagonal(closure, True) 
        for k in range(n):
            closure = closure | (closure[:, k:k+1] & closure[k:k+1, :])
        return closure

    def closure_cached(self, delta_frozen: frozenset[Literal]) -> Set[Literal]:
        """Cached version of closure for frequently accessed sets."""
        # Use instance-level cache instead of @lru_cache
        if delta_frozen not in self._closure_cache:
            self._closure_cache[delta_frozen] = self._closure_matrix(delta_frozen)
        return self._closure_cache[delta_frozen]

    def _closure_matrix(self, delta: Iterable[Literal]) -> Set[Literal]:
        """Matrix-based closure computation."""
        delta_set = set(delta)
        unknown = delta_set - self.assumptions
        if unknown:
            raise ValueError(f"closure() called with literals not in assumptions: {unknown}")
        
        # Convert to indices
        indices = [self._assumption_idx[a] for a in delta_set]
        n = len(self._assumption_list)
        
        # Create boolean vector for delta
        in_set = np.zeros(n, dtype=bool)
        in_set[indices] = True
        
        # Compute closure: everything reachable via support
        # For each element in delta, add everything it transitively supports
        for idx in indices:
            in_set |= self._support_closure[idx]
        
        # Convert back to literals
        result = {self._assumption_list[i] for i in np.where(in_set)[0]}
        return result    
    # --- public views ---
    def support_from(self, a: Literal) -> Set[Literal]:
        return self._support_from.get(a, set())

    def attack_from(self, a: Literal) -> Set[Literal]:
        return self._attack_from.get(a, set()) 

    def closure(self, delta: Iterable[Literal]) -> Set[Literal]:
        """
        Compute Cl(delta): start with delta, add all assumptions reachable via support rules.
        Only assumptions can appear in the result (by definition).
        """
        # Normalise & validate input
        result: Set[Literal] = set(delta)
        unknown = result - self.assumptions
        if unknown:
            raise ValueError(f"closure() called with literals not in assumptions: { {u.key for u in unknown} }")

        # BFS over support edges
        queue = list(result)
        while queue:
            a = queue.pop()
            for sup in self._support_from.get(a, ()):
                if sup not in result:
                    result.add(sup)
                    queue.append(sup)
        return result

    def is_closed(self, delta: Iterable[Literal]) -> bool:
        """Check if delta == Cl(delta)."""
        dset = set(delta)
        return dset == self.closure(dset)

    def derives(self, delta: Iterable[Literal], target: Literal) -> bool:
        """
        Δ ⊢ target ?
        - If target is an assumption: membership in Cl(Δ).
        - If target is a contrary ¯β: exists α ∈ Cl(Δ) with rule ¯β ← α.
        """
        dset = set(delta)
        if not dset.issubset(self.assumptions):
            bad = {x.key for x in dset - self.assumptions}
            raise ValueError(f"derives() given literals not in assumptions: {bad}")

        cl = self.closure(dset)

        if target in self.assumptions:
            return target in cl

        if target in self._inv_contrary:  # it's a contrary
            attacked = self._inv_contrary[target]
            return any(attacked in self._attack_from[a] for a in cl)

        raise ValueError(f"Unknown target literal {target.key}")

    def attacks(self, delta: Iterable[Literal], beta: Literal) -> bool:
        """Δ attacks β  ⇔  Δ derives ¯β."""
        if beta not in self.assumptions:
            raise ValueError(f"attacks() expects an assumption, got {beta.key}")
        return self.derives(delta, self.contrary[beta])

    def attacks_set(self, delta: Iterable[Literal], Bs: Iterable[Literal]) -> bool:
        """Δ attacks B iff it attacks at least one β ∈ B."""
        return any(self.attacks(delta, b) for b in Bs)

    def conflict_free(self, delta: Iterable[Literal]) -> bool:
        """
        Δ is conflict-free iff it does not attack any of its own members.
        (We over-approx with the whole Δ; if a subset attacks, Δ attacks too.)
        """
        dset = set(delta)
        if not dset.issubset(self.assumptions):
            bad = {x.key for x in dset - self.assumptions}
            raise ValueError(f"conflict_free() got non-assumptions: {bad}")

        cl = self.closure(dset)
        for x in dset:
            # any attacker of x reachable from Δ ?
            if any(x in self._attack_from[a] for a in cl):
                return False
        return True


    def _closed_attackers_of(self, alpha: Literal) -> list[Set[Literal]]:
        """
        Heuristic but sufficient in Bipolar ABA:
        any attack on α must end with a rule ¬α ← a  (single body).
        So consider closures of each direct attacker 'a'.
        """
        if alpha not in self.assumptions:
            raise ValueError(f"_closed_attackers_of expects an assumption, got {alpha.key}")

        direct_attackers = {a for a in self.assumptions if alpha in self._attack_from[a]}
        return [self.closure({a}) for a in direct_attackers]


    def defends(self, delta: Iterable[Literal], alpha: Literal) -> bool:
        """
        Δ defends α iff for every closed attacker B of α, Δ attacks B.
        We instantiate closed attackers as closures of single attackers (see above).
        """
        dset = set(delta)
        if alpha not in self.assumptions:
            raise ValueError(f"defends() expects an assumption for alpha, got {alpha.key}")
        if not dset.issubset(self.assumptions):
            bad = {x.key for x in dset - self.assumptions}
            raise ValueError(f"defends() got non-assumptions in delta: {bad}")

        for B in self._closed_attackers_of(alpha):
            # B is closed and (by construction) attacks alpha
            if not self.attacks_set(dset, B):
                return False
        return True

    def defends_set(self, delta: Iterable[Literal], gamma: Iterable[Literal]) -> bool:
        """Δ defends every β ∈ Γ."""
        gset = set(gamma)
        return all(self.defends(delta, b) for b in gset)

    def defended_by(self, delta: Iterable[Literal]) -> Set[Literal]:
        """{ α ∈ A | Δ defends α }"""
        dset = set(delta)
        return {a for a in self.assumptions if self.defends(dset, a)}

    # generic back-tracking over admissible supersets, with extra filter (for finding extensions)
    def _enum_with_filter(
        self,
        keep_fn: Callable[[Set[Literal]], bool],
        need_maximal: bool = False,
    ) -> list[Set[Literal]]:
        """Parallelized enumeration with matrix-based pruning."""
        # always use SAT solver
        return self._enum_sat(keep_fn, need_maximal)

    def _enum_sat(
        self,
        keep_fn: Callable[[Set[Literal]], bool],
        need_maximal: bool = False,
    ) -> list[Set[Literal]]:
        """SAT-based enumeration with proper model blocking + dedup by closed set."""
        try:
            from pysat.solvers import Glucose4
            from tqdm import tqdm
        except ImportError:
            print("  ⚠️ python-sat or tqdm not installed")
            print("     Install with: pip install python-sat tqdm")
            return self._enum_with_filter_sequential(keep_fn, need_maximal)

        n = len(self.assumptions)
        print(f"\n🔧 SAT-based search of {n} assumptions")

        results: list[Set[Literal]] = []
        seen_closed: set[frozenset[Literal]] = set()  # dedup by CLOSED set

        # Use a stable ordering to map vars ↔ assumptions
        assumps = list(self.assumptions)  # could also use self._assumption_list if you prefer
        var_to_arg = {i + 1: a for i, a in enumerate(assumps)}
        arg_to_var = {a: i + 1 for i, a in enumerate(assumps)}
        all_vars = list(var_to_arg.keys())

        solver = Glucose4()

        # --- Phase 1: conflict-free clauses ---
        print(f"\n📊 Encoding conflict-free constraints...")
        conflict_constraints = 0
        with tqdm(total=n, desc="  Processing assumptions", unit="assumption") as pbar:
            for a in assumps:
                a_var = arg_to_var[a]
                closed_a = self.closure({a})
                # If anything in closure({a}) attacks b, forbid picking both a and b
                for b in assumps:
                    if any(b in self._attack_from.get(c, set()) for c in closed_a):
                        b_var = arg_to_var[b]
                        solver.add_clause([-a_var, -b_var])
                        conflict_constraints += 1
                pbar.update(1)
                pbar.set_postfix({"constraints": conflict_constraints})
        print(f"  ✓ Added {conflict_constraints:,} conflict-free constraints")

        # --- Phase 2: admissibility (defence) clauses ---
        print(f"\n🛡️ Encoding admissibility constraints...")
        attackers_map: dict[Literal, list[Literal]] = {}
        # Find attackers for each a
        with tqdm(total=n, desc="  Finding attackers", unit="assumption") as pbar:
            for a in assumps:
                attackers: list[Literal] = []
                for b in assumps:
                    closed_b = self.closure({b})
                    if any(a in self._attack_from.get(c, set()) for c in closed_b):
                        attackers.append(b)
                attackers_map[a] = attackers
                pbar.update(1)
                pbar.set_postfix({"total_attackers": sum(len(v) for v in attackers_map.values())})

        defense_constraints = 0
        with tqdm(total=n, desc="  Encoding defenses", unit="assumption") as pbar:
            for a in assumps:
                a_var = arg_to_var[a]
                for attacker in attackers_map[a]:
                    # defenders = { c | closure({c}) attacks attacker }
                    defenders_vars = []
                    for c in assumps:
                        closed_c = self.closure({c})
                        if any(attacker in self._attack_from.get(d, set()) for d in closed_c):
                            defenders_vars.append(arg_to_var[c])

                    if defenders_vars:
                        # if pick 'a' then at least one defender must be in
                        solver.add_clause([-a_var] + defenders_vars)
                    else:
                        # no way to defend 'a' against this attacker ⇒ cannot pick 'a'
                        solver.add_clause([-a_var])
                    defense_constraints += 1
                pbar.update(1)
                pbar.set_postfix({"constraints": defense_constraints})
        print(f"  ✓ Added {defense_constraints:,} defense constraints")

        # --- Phase 3: enumerate models ---
        print(f"\n🔍 Finding admissible extensions...")
        spinner = Spinner("Finding solutions")
        spinner.start()

        solutions_found = 0
        sat_calls = 0

        try:
            while solver.solve():
                sat_calls += 1
                model = solver.get_model()

                # Extract the chosen assumptions from the model (positives only)
                true_vars = {lit for lit in model if lit > 0 and lit in var_to_arg}
                extension = {var_to_arg[v] for v in true_vars}

                # We only keep CLOSED sets (and test admissibility on the closed set)
                closed = self.closure(extension)

                if self.is_admissible(closed) and keep_fn(closed):
                    fz = frozenset(closed)
                    if fz not in seen_closed:
                        seen_closed.add(fz)
                        results.append(closed)
                        solutions_found += 1

                spinner.update_stats(calls=sat_calls, found=solutions_found)

                # Block the ENTIRE current assignment across all variables
                # (classic model enumeration blocking).
                # For variable v:
                #   if v was True  → add ¬v
                #   if v was False → add  v
                model_pos = set(true_vars)
                blocking_clause = [(-v if v in model_pos else v) for v in all_vars]
                solver.add_clause(blocking_clause)

                # (Optional early-stop removed; enumeration is cheap in these unit tests.)
        finally:
            spinner.stop(f"✓ Found {solutions_found} unique extensions with {sat_calls} SAT calls")

        # --- Maximality filter (preferred etc.) ---
        if need_maximal and len(results) > 1:
            print(f"\n🔝 Filtering {len(results)} extensions for maximality...")
            with tqdm(total=len(results), desc="  Checking maximality") as pbar:
                maximal = []
                results.sort(key=len, reverse=True)
                for i, ext in enumerate(results):
                    is_max = True
                    for j in range(i):
                        if ext < results[j]:
                            is_max = False
                            break
                    if is_max:
                        maximal.append(ext)
                    pbar.update(1)
                    pbar.set_postfix({"maximal": len(maximal)})
            print(f"  ✓ Found {len(maximal)} maximal extensions")
            return maximal

        return results


    def _filter_maximal_sat(self, extensions: list[Set[Literal]]) -> list[Set[Literal]]:
        """
        Efficiently filter for maximal sets using size-based pruning.
        """
        if not extensions:
            return []
        
        # Sort by size (largest first)
        extensions.sort(key=len, reverse=True)
        
        maximal = []
        for i, ext in enumerate(extensions):
            is_maximal = True
            
            # Only need to check against larger or equal-sized sets
            for j in range(i):
                if ext < extensions[j]:  # ext is proper subset
                    is_maximal = False
                    break
            
            if is_maximal:
                maximal.append(ext)
        
        print(f"    Found {len(maximal)} maximal extensions")
        return maximal

    def _enum_with_filter_sequential(
        self,
        keep_fn: Callable[[Set[Literal]], bool],
        need_maximal: bool = False,
    ) -> list[Set[Literal]]:
        """Sequential enumeration with activity spinner."""
        ordered = tuple(sorted(self.assumptions, key=lambda l: l.key))
        seen: set[frozenset[Literal]] = set()
        results: list[Set[Literal]] = []
        
        # Statistics
        nodes_visited = [0]
        last_update_time = [time.time()]
        
        # Start spinner
        n = len(ordered)
        spinner = Spinner(f"Searching {n} assumptions")
        spinner.start()
        
        def update_spinner():
            """Update spinner statistics periodically."""
            current_time = time.time()
            if current_time - last_update_time[0] > 0.5:  # Update every 0.5 seconds
                spinner.update_stats(
                    visited=f"{nodes_visited[0]:,}",
                    found=len(results),
                    unique=len(seen)
                )
                last_update_time[0] = current_time

        def dfs(current: Set[Literal], start_idx: int) -> None:
            # DON'T close current here - it represents explicitly chosen assumptions
            cur_f = frozenset(current)
            if cur_f in seen:
                return
            seen.add(cur_f)
            
            # Check if the CLOSURE is admissible
            current_closed = self.closure(current)
            if self.is_admissible(current_closed) and keep_fn(current_closed):
                results.append(current_closed)  # Store the closed version
            
            for i in range(start_idx, len(ordered)):
                a = ordered[i]
                if a in current:  # Check against explicitly chosen
                    continue
                new_set = self.closure(current | {a})  # Get closure for checking
                if not self.conflict_free(new_set):
                    continue
                if not self.defends_set(new_set, new_set):
                    continue
                dfs(current | {a}, i + 1)  # Pass NON-CLOSED (explicitly chosen)

        try:
            dfs(set(), 0)
        finally:
            spinner.stop(f"✓ Search complete: {nodes_visited[0]:,} nodes visited, {len(results)} extensions found")

        if need_maximal:
            spinner = Spinner(f"Filtering {len(results)} sets for maximality")
            spinner.start()
            
            try:
                checked = [0]
                maximal = []
                for i, S in enumerate(results):
                    checked[0] = i + 1
                    if i % 10 == 0:
                        spinner.update_stats(
                            checked=f"{checked[0]}/{len(results)}",
                            maximal=len(maximal)
                        )
                    
                    if not any(S < T for T in results):
                        maximal.append(S)
                
                spinner.stop(f"✓ Found {len(maximal)} maximal extensions")
                return maximal
            except:
                spinner.stop()
                raise
        
        return results

    def _is_admissible_fast(self, delta: Set[Literal]) -> bool:
        """Fast admissibility check using cached operations."""
        delta_frozen = frozenset(delta)
        closed = self.closure_cached(delta_frozen)
        return (closed == delta and 
                self._conflict_free_matrix(closed) and 
                self._defends_set_matrix(closed, closed))

    def _conflict_free_matrix(self, delta: Set[Literal]) -> bool:
        """Matrix-based conflict-free check."""
        indices = [self._assumption_idx[a] for a in delta]
        if not indices:
            return True
        
        # Check if any element in delta attacks another
        delta_vec = np.zeros(len(self._assumption_list), dtype=bool)
        delta_vec[indices] = True
        
        # For each element in closure of delta
        closure = self.closure_cached(frozenset(delta))
        closure_indices = [self._assumption_idx[a] for a in closure]
        
        # Check if closure attacks any element in delta
        for idx in closure_indices:
            if np.any(self._attack_matrix[idx] & delta_vec):
                return False
        return True

    def _defends_set_matrix(self, delta: Set[Literal], gamma: Set[Literal]) -> bool:
        """Matrix-based defense check."""
        # Convert to indices
        delta_indices = [self._assumption_idx[a] for a in delta]
        gamma_indices = [self._assumption_idx[a] for a in gamma]
        
        if not gamma_indices:
            return True
        
        # For each element in gamma, check if delta defends it
        for g_idx in gamma_indices:
            # Find all attackers of g
            attackers = np.where(self._attack_matrix[:, g_idx])[0]
            
            for att_idx in attackers:
                # Check if delta attacks the attacker's closure
                att_literal = self._assumption_list[att_idx]
                att_closure = self.closure_cached(frozenset([att_literal]))
                
                if not self.attacks_set(delta, att_closure):
                    return False
        
        return True

    def _can_extend(self, current: Set[Literal]) -> bool:
        """Quick check if current set can potentially be extended."""
        # If current is not conflict-free, no point extending
        return self._conflict_free_matrix(current)

    def _quick_conflict_check(self, delta: Set[Literal]) -> bool:
        """Quick conflict check using matrices."""
        return not self._conflict_free_matrix(delta)

    def _filter_maximal_matrix(self, sets: list[Set[Literal]]) -> list[Set[Literal]]:
        """Filter maximal sets with progress bar."""
        if not sets:
            return []
        
        print(f"\n Filtering {len(sets)} sets for maximality...")
        
        n_sets = len(sets)
        n_assumptions = len(self._assumption_list)
        
        # Convert to matrix with progress
        matrix = np.zeros((n_sets, n_assumptions), dtype=bool)
        for i in tqdm(range(n_sets), desc="Converting to matrix", leave=False):
            for a in sets[i]:
                matrix[i, self._assumption_idx[a]] = True
        
        # Find maximal sets with progress
        is_maximal = np.ones(n_sets, dtype=bool)
        
        with tqdm(total=n_sets, desc="Checking maximality", leave=True) as pbar:
            for i in range(n_sets):
                if not is_maximal[i]:
                    pbar.update(1)
                    continue
                    
                # Check against all other sets
                for j in range(n_sets):
                    if i == j or not is_maximal[j]:
                        continue
                    # Check if sets[i] ⊂ sets[j]
                    if np.all(matrix[i] <= matrix[j]) and not np.array_equal(matrix[i], matrix[j]):
                        is_maximal[i] = False
                        break
                
                pbar.update(1)
                pbar.set_postfix({"maximal_found": is_maximal.sum()})
        
        result = [sets[i] for i in range(n_sets) if is_maximal[i]]
        print(f"✓ Found {len(result)} maximal sets")
        return result



    def is_admissible(self, delta: Iterable[Literal]) -> bool:
        dset = set(delta)
        return self.is_closed(dset) and self.conflict_free(dset) and self.defends_set(dset, dset)

    def admissible_extensions(self) -> list[Set[Literal]]:
        print("\n Computing admissible extensions...")
        return self._enum_with_filter(lambda _: True)

    def preferred_extensions(self) -> list[Set[Literal]]:
        print("\n Computing preferred extensions...")
        return self._enum_with_filter(lambda _: True, need_maximal=True)

    def is_complete(self, delta: Iterable[Literal]) -> bool:
        dset = set(delta)
        return (
            self.is_admissible(dset)
            and dset == self.closure(self.defended_by(dset))        # fix-point condition
        )

    def complete_extensions(self) -> list[Set[Literal]]:
        print("\n Computing complete extensions...")
        return self._enum_with_filter(self.is_complete) 

    def is_set_stable(self, delta: Iterable[Literal]) -> bool:
        dset = set(delta)
        if not (self.is_closed(dset) and self.conflict_free(dset)):
            return False
        outsiders = self.assumptions - dset
        for beta in outsiders:
            if not self.attacks_set(dset, self.closure({beta})):
                return False
        return True

    def set_stable_extensions(self) -> list[Set[Literal]]:
        print("\n Computing set stable extensions...")
        return self._enum_with_filter(self.is_set_stable)

    def well_founded_extension(self) -> Set[Literal] | None:
        comps = self.complete_extensions()
        if not comps:
            return None
        inter = set.intersection(*map(set, comps))
        return inter

    def ideal_extensions(self) -> list[Set[Literal]]:
        print("\n Computing ideal extensions...")
        prefs = self.preferred_extensions()
        if not prefs:
            return []      # definition vacuous if no preferred
        def subset_of_all_pref(S: Set[Literal]) -> bool:
            return all(S.issubset(P) for P in prefs)
        # need ⊆-max admissible sets that are subset of every preferred
        return self._enum_with_filter(subset_of_all_pref, need_maximal=True)

    
    def get_fact_attacks(self) -> list[dict]:
        """
        Find all assumptions that are attacked by fact nodes.
        
        Returns:
            List of dicts with format:
            {
                'fact_id': str,
                'fact_text': str,
                'attacks': [
                    {'assumption_id': str, 'assumption_text': str},
                    ...
                ]
            }
        """
        fact_attacks = []
        
        # Find all fact nodes
        facts = [a for a in self.assumptions if a.type == LiteralType.FACT]
        
        for fact in facts:
            attacks = []
            
            # Check what this fact attacks
            for attacked in self._attack_from.get(fact, set()):
                attacks.append({
                    'assumption_id': attacked.key,
                    'assumption_text': str(attacked.payload) if attacked.payload else attacked.key
                })
            
            if attacks:  # Only include facts that actually attack something
                fact_attacks.append({
                    'fact_id': fact.key,
                    'fact_text': str(fact.payload) if fact.payload else fact.key,
                    'attacks': attacks
                })
        
        return fact_attacks

    def print_fact_attacks(self) -> None:
        """
        Pretty print all fact-based attacks in the framework.
        """
        fact_attacks = self.get_fact_attacks()
        
        if not fact_attacks:
            print("📊 No fact-based attacks found in the framework")
            return
        
        print(f"\n📊 Fact-based attacks ({len(fact_attacks)} facts attacking assumptions):")
        print("=" * 80)
        
        for fact_info in fact_attacks:
            print(f"\n✓ Fact: {fact_info['fact_id']}")
            print(f"  Content: \"{fact_info['fact_text'][:150]}...\"")
            print(f"  Attacks {len(fact_info['attacks'])} assumption(s):")
            
            for attacked in fact_info['attacks']:
                print(f"    ❌ {attacked['assumption_id']}: \"{attacked['assumption_text'][:100]}...\"")
        
        print("=" * 80)

    def _map_vars(self):
        """Stable var mapping: integer var <-> assumption Literal."""
        assumps = sorted(self.assumptions, key=lambda l: l.key)
        var_to_arg = {i + 1: a for i, a in enumerate(assumps)}
        arg_to_var = {a: i + 1 for i, a in enumerate(assumps)}
        var_list = list(var_to_arg.keys())
        return assumps, var_to_arg, arg_to_var, var_list


    def _add_conflict_free(self, solver: Glucose4, arg_to_var: Dict[Literal, int]) -> int:
        """Encode conflict-free; returns number of clauses added, with a progress bar."""
        cnt = 0
        assumps = sorted(self.assumptions, key=lambda l: l.key)
        n = len(assumps)
        print("\n📊 Encoding conflict-free constraints...")
        with tqdm(total=n, desc="  Processing assumptions", unit="assumption") as pbar:
            for a in assumps:
                a_var = arg_to_var[a]
                closed_a = self.closure({a})
                for b in assumps:
                    if any(b in self._attack_from.get(c, set()) for c in closed_a):
                        b_var = arg_to_var[b]
                        solver.add_clause([-a_var, -b_var])
                        cnt += 1
                pbar.update(1)
                pbar.set_postfix({"constraints": cnt})
        print(f"  ✓ Added {cnt:,} conflict-free constraints")
        return cnt


    def _add_admissibility(self, solver: Glucose4, arg_to_var: Dict[Literal, int]) -> int:
        """Encode defense constraints; returns number of clauses, with progress bars."""
        cnt = 0
        assumps = sorted(self.assumptions, key=lambda l: l.key)
        n = len(assumps)

        print("\n🛡️ Encoding admissibility constraints...")
        attackers_map: Dict[Literal, List[Literal]] = {}

        # Find attackers per a
        with tqdm(total=n, desc="  Finding attackers", unit="assumption") as pbar:
            total_attackers = 0
            for a in assumps:
                attackers: List[Literal] = []
                for b in assumps:
                    closed_b = self.closure({b})
                    if any(a in self._attack_from.get(c, set()) for c in closed_b):
                        attackers.append(b)
                attackers_map[a] = attackers
                total_attackers += len(attackers)
                pbar.update(1)
                pbar.set_postfix({"total_attackers": total_attackers})

        # Encode defenses
        with tqdm(total=n, desc="  Encoding defenses", unit="assumption") as pbar:
            for a in assumps:
                a_var = arg_to_var[a]
                for attacker in attackers_map[a]:
                    defenders_vars = []
                    for c in assumps:
                        closed_c = self.closure({c})
                        if any(attacker in self._attack_from.get(d, set()) for d in closed_c):
                            defenders_vars.append(arg_to_var[c])

                    if defenders_vars:
                        solver.add_clause([-a_var] + defenders_vars)
                    else:
                        solver.add_clause([-a_var])  # cannot defend a against this attacker
                    cnt += 1
                pbar.update(1)
                pbar.set_postfix({"constraints": cnt})
        print(f"  ✓ Added {cnt:,} defense constraints")
        return cnt


    def _add_closure_implications(self, solver: Glucose4, arg_to_var: Dict[Literal, int]) -> int:
        """
        Enforce closedness: for each reachability a ⟹ b add (¬a ∨ b).
        Shows progress across the n×n scan.
        """
        n = len(self._assumption_list)
        if n == 0:
            return 0
        print("\n🧩 Encoding closure (reachability) implications...")
        cnt = 0
        with tqdm(total=n, desc="  From a", unit="row") as prow:
            for i in range(n):
                ai = self._assumption_list[i]
                vi = arg_to_var[ai]
                # iterate columns j
                for j in range(n):
                    if i == j:
                        continue
                    if self._support_closure[i, j]:
                        bj = self._assumption_list[j]
                        vj = arg_to_var[bj]
                        solver.add_clause([-vi, vj])
                        cnt += 1
                prow.update(1)
                prow.set_postfix({"implications": cnt})
        print(f"  ✓ Added {cnt:,} closure implications")
        return cnt



    def _build_solver_for_admissible(self) -> Glucose4:
        """Create a solver with (closed ∧ conflict-free ∧ defended) constraints, with progress."""
        _, _, arg_to_var, _ = self._map_vars()
        solver = Glucose4()
        _ = self._add_conflict_free(solver, arg_to_var)
        _ = self._add_admissibility(solver, arg_to_var)
        _ = self._add_closure_implications(solver, arg_to_var)
        return solver


    def _solve_with_bound(self, sense: str, bound: int) -> Glucose4:
        """
        Make a solver with base constraints + a cardinality bound on |Δ|.
        Shows progress while adding the cardinality constraint and a spinner while solving.
        """
        assumps, _, _, var_list = self._map_vars()
        print(f"\n🧮 Building solver with cardinality: {sense} {bound}")
        solver = self._build_solver_for_admissible()

        # Add the cardinality constraint
        if sense == "atleast":
            cnf = CardEnc.atleast(lits=var_list, bound=bound, encoding='seqcounter')
        elif sense == "equals":
            cnf = CardEnc.equals(lits=var_list, bound=bound, encoding='seqcounter')
        elif sense == "atmost":
            cnf = CardEnc.atmost(lits=var_list, bound=bound, encoding='seqcounter')
        else:
            raise ValueError("sense must be 'atleast', 'equals', or 'atmost'")

        with tqdm(total=len(cnf.clauses), desc="  Adding cardinality clauses", unit="clause") as pbar:
            for cl in cnf.clauses:
                solver.add_clause(cl)
                pbar.update(1)

        # We return the solver; the caller may call solve() repeatedly.
        return solver

    def _model_to_set(self, model: List[int]) -> Set[Literal]:
        _, var_to_arg, _, var_list = self._map_vars()
        pos = set(l for l in model if l > 0)
        return {var_to_arg[v] for v in var_list if v in pos}


    def admissible_extensions_topk(self, k: int) -> List[Set[Literal]]:
        """
        Exact top-k by size for admissible semantics.
        Returns up to k CLOSED admissible sets, starting with the largest size.
        Shows progress/spinners during search.
        """
        if k <= 0:
            return []

        n = len(self.assumptions)
        print("\n🏁 Top-k admissible search")

        # ---- Phase 1: find maximum cardinality via binary search on |Δ|
        print("🔎 Phase 1: locating maximum admissible size (binary search)")
        lo, hi = 0, n
        best_size = 0
        steps = int(np.floor(np.log2(n))) + 2 if n > 0 else 1
        with tqdm(total=steps, desc="  Probing sizes", unit="step") as pbar:
            while lo <= hi:
                mid = (lo + hi) // 2
                spinner = Spinner(f"solve(|Δ| ≥ {mid})")
                spinner.start()
                s = self._solve_with_bound("atleast", mid)
                sat = s.solve()
                spinner.stop(f"  → {'SAT' if sat else 'UNSAT'} for ≥ {mid}")
                if sat:
                    best_size = mid
                    lo = mid + 1
                else:
                    hi = mid - 1
                pbar.update(1)
                pbar.set_postfix({"best": best_size})
        print(f"✅ Maximum admissible size = {best_size}")

        results: List[Set[Literal]] = []
        seen = set()

        # helper to enumerate all at exact size 'size', but stop when we have k
        def enumerate_at_size(size: int):
            nonlocal results
            if size < 0 or len(results) >= k:
                return
            print(f"\n📦 Enumerating admissible sets with |Δ| = {size}")
            s = self._solve_with_bound("equals", size)
            found_here = 0
            spinner = Spinner("enumerate models")
            spinner.start()
            try:
                while len(results) < k and s.solve():
                    model = s.get_model()
                    ext = self._model_to_set(model)  # already closed by construction
                    fext = frozenset(ext)
                    if fext not in seen:
                        seen.add(fext)
                        results.append(ext)
                        found_here += 1
                    # block this exact model by negating its positive vars
                    _, _, _, var_list = self._map_vars()
                    pos = [v for v in var_list if v in set(l for l in model if l > 0)]
                    s.add_clause([-v for v in pos])
                    spinner.update_stats(found=len(results))
            finally:
                spinner.stop(f"✓ Found {found_here} at size {size}")

        # enumerate at the maximum size
        enumerate_at_size(best_size)

        # if caller wants more than exist at max size, drop to next sizes
        size = best_size - 1
        while len(results) < k and size >= 0:
            enumerate_at_size(size)
            size -= 1

        print(f"\n🎯 Returning {len(results)} set(s)")
        return results


    def preferred_extensions_topk(self, k: int) -> List[Set[Literal]]:
        """
        Preferred = ⊆-maximal admissible. Every maximum-cardinality admissible set is preferred.
        So: enumerate top-k largest admissible sets. If more than k exist at max size,
        any k of them is fine.
        """
        print("\n⭐ Top-k preferred via top-k admissible (largest first)")
        return self.admissible_extensions_topk(k)



    def build_derivation_tree(self, delta: Iterable["Literal"], goal: "Literal") -> "DerivationTree | None":
        """
        Return ONE derivation tree of `goal` from Δ, or None if goal not derivable.
        Works under Bipolar-ABA’s single-body rule restriction.
        """
        # we work with the closure once
        base = set(delta)
        if not base.issubset(self.assumptions):
            raise ValueError("Δ must contain only assumptions")

        cl = self.closure(base)

        # recursive helper
        def derive(target: Literal) -> DerivationNode | None:
            # 1. leaf?  (target directly provided by Δ)
            if target in base:
                return DerivationNode(target, None, None)

            # 2. support rule head?
            for body in cl:
                if target in self._support_from[body]:
                    child = derive(body)
                    if child:
                        return DerivationNode(target, Rule(target, body), child)

            # 3. contrary head?
            if target in self._inv_contrary:           # target = ¬β
                attacked = self._inv_contrary[target]
                for body in cl:
                    if attacked in self._attack_from[body]:
                        child = derive(body)
                        if child:
                            return DerivationNode(target, Rule(target, body), child)

            return None  # no derivation found

        root_node = derive(goal)
        return DerivationTree(root_node) if root_node else None
    #  Enumerate *all* derivation trees for a goal from Δ
    def build_all_derivation_trees(
        self,
        delta: Iterable["Literal"],
        goal: "Literal",
        max_paths: int | None = None,           # optional cut-off
    ) -> list["DerivationTree"]:
        """
        Return a list of DerivationTree objects, one for each distinct path that
        derives `goal` from Δ.  Stops early after `max_paths` (if given).
        """
        base = set(delta)
        if not base.issubset(self.assumptions):
            raise ValueError("Δ must contain only assumptions")

        cl = self.closure(base)
        trees: list[DerivationTree] = []

        def dfs(target: Literal, seen: set[Literal]) -> list[DerivationNode]:
            """Return all DerivationNode roots that derive `target`."""
            if target in seen:                                   # avoid cycles
                return []
            if max_paths is not None and len(trees) >= max_paths:
                return []

            # case 1: leaf
            if target in base:
                return [DerivationNode(target, None, None)]

            results: list[DerivationNode] = []

            # case 2: support rules
            for body in self.assumptions:
                if body in cl and target in self._support_from[body]:
                    for child in dfs(body, seen | {target}):
                        results.append(
                            DerivationNode(target, Rule(target, body), child)
                        )

            # case 3: attack rules if target is a contrary
            if target in self._inv_contrary:
                attacked = self._inv_contrary[target]
                for body in cl:
                    if attacked in self._attack_from[body]:
                        for child in dfs(body, seen | {target}):
                            results.append(
                                DerivationNode(target, Rule(target, body), child)
                            )

            return results

        roots = dfs(goal, set())
        for r in roots:
            trees.append(DerivationTree(r))
            if max_paths is not None and len(trees) >= max_paths:
                break
        return trees

    def build_dialectical_tree(
        self,
        delta: Iterable["Literal"],
        alpha: "Literal",
        semantics: str = "admissible",
        max_depth: int | None = None,
    ) -> "DialecticalTree":
        """
        Build a dialogue tree under the chosen semantics.
        semantics ∈ {"admissible", "preferred"} #TODO: Implement the others too!
        """
        drv_cls = {
            "admissible": AdmissibleDriver,
            "preferred":  PreferredDriver,
            "complete":   CompleteDriver,
            "set-stable": SetStableDriver,
            "well-founded": WellFoundedDriver,
            "ideal":      IdealDriver,
        }.get(semantics)
        if drv_cls is None:
            raise ValueError(f"unsupported semantics {semantics!r}")
        driver = drv_cls(self)

        Δ = set(delta)
        if alpha not in self.assumptions:
            raise ValueError("alpha must be an assumption")
        if not Δ.issubset(self.assumptions):
            raise ValueError("Δ must contain only assumptions")

        root = DialecticalNode("pro", Δ, alpha)

        def expand(node: DialecticalNode, depth: int):
            if max_depth is not None and depth >= max_depth:
                return

            if node.role == "pro":
                if node.target is None:
                    return  # nothing to defend at this level
                for B in driver.closed_attackers(node.target):
                    opp = DialecticalNode("opp", B, node.target)
                    node.children.append(opp)
                    expand(opp, depth + 1)

            else:  # node.role == "opp"
                B = node.support_set
                # minimal counter-attack: find some subset of Δ that attacks B
                attacker = next(( {x} for x in Δ if self.attacks({x}, next(iter(B))) ),
                                None)
                if attacker is None and self.attacks_set(Δ, B):
                    attacker = Δ
                if attacker:
                    pro = DialecticalNode("pro", attacker, None)
                    node.children.append(pro)
                    # optional deeper defence on each β in B
                    if semantics not in {"admissible", "preferred"}:
                        for beta in B:
                            child = DialecticalNode("pro", attacker, beta)
                            pro.children.append(child)
                            expand(child, depth + 2)

        expand(root, 0)

        # apply extra burden (e.g. maximality) at root
        if not driver.extra_burden(root.support_set):
            root.children.append(
                DialecticalNode("fail", set(), None)  # marks unmet burden
            )
        return DialecticalTree(root)

    def is_complete(self, delta):    return CompleteDriver(self).extra_burden(set(delta)) and self.is_admissible(delta)
    def is_set_stable(self, delta):  return SetStableDriver(self).extra_burden(set(delta))
    def is_well_founded(self, delta):return WellFoundedDriver(self).extra_burden(set(delta))
    def is_ideal(self, delta):       return IdealDriver(self).extra_burden(set(delta))

    # The extra_burdens can be utilized as flags 
    # Since we use is_admissible etc. (what we defined before) in the computation of these sets, 
    # those stay the same
    def derivation_dag(
        self,
        delta: Iterable["Literal"],
        goal: "Literal",
        max_paths: int | None = None,
    ) -> "DerivationDAG":
        trees = self.build_all_derivation_trees(delta, goal, max_paths)
        return DerivationDAG(trees)

    def graph(self, include_contraries: bool = False) -> "FrameworkGraph":
        """Return a FrameworkGraph object for visualisation."""
        return FrameworkGraph(self, include_contraries)


class _BaseDriver:
    """Abstract helper—concrete subclasses below."""
    def __init__(self, F: "BipolarABA"):
        self.F = F

    # --- required hooks ---                                     
    def closed_attackers(self, alpha: "Literal") -> list[Set["Literal"]]:
        raise NotImplementedError

    def pro_can_answer(self, B: Set["Literal"], delta: Set["Literal"]) -> bool:
        raise NotImplementedError

    # In case we don't set it up or it's not loaded properly

    def extra_burden(self, pro_set: Set["Literal"]) -> bool:
        """Checks maximality, fixpoints, etc.  Pass-through for admissible."""
        return True


class AdmissibleDriver(_BaseDriver):
    """Default admissible semantics."""
    def closed_attackers(self, alpha):
        return self.F._closed_attackers_of(alpha)

    def pro_can_answer(self, B, delta):
        return self.F.attacks_set(delta, B)


class PreferredDriver(AdmissibleDriver):
    """⊆-maximal admissible."""
    def extra_burden(self, pro_set):
        # Δ is ⊆-maximal admissible iff no admissible superset exists.
        for a in self.F.assumptions - pro_set:
            sup = self.F.closure(pro_set | {a})
            if self.F.is_admissible(sup):
                return False
        return True

class CompleteDriver(AdmissibleDriver):
    """Admissible + fix-point: Δ must contain every literal it defends."""
    def extra_burden(self, pro_set):
        return pro_set == self.F.defended_by(pro_set)

class SetStableDriver(_BaseDriver):
    """
    Δ is set-stable ⇔ Δ is closed, conflict-free, and
    Δ attacks Cl({β}) for every β ∉ Δ.
    """
    def closed_attackers(self, alpha):
        # not used; set-stable is global, but needs to be defined to not raise an error
        return []

    def pro_can_answer(self, B, delta):
        return self.F.attacks_set(delta, B)

    def extra_burden(self, pro_set):
        if not (self.F.is_closed(pro_set) and self.F.conflict_free(pro_set)):
            return False
        outsiders = self.F.assumptions - pro_set
        for beta in outsiders:
            if not self.F.attacks_set(pro_set, self.F.closure({beta})):
                return False
        return True

class WellFoundedDriver(CompleteDriver):
    """
    Δ must equal the intersection of all complete extensions.
    """
    def extra_burden(self, pro_set):
        wf = self.F.well_founded_extension()
        return wf is not None and wf == pro_set

class IdealDriver(AdmissibleDriver):
    """
    Δ admissible AND ⊆ every preferred extension, AND ⊆-max among such sets.
    """
    def extra_burden(self, pro_set):
        prefs = self.F.preferred_extensions()
        if not prefs:
            return False
        # subset of all preferred?
        if not all(pro_set.issubset(P) for P in prefs):
            return False
        # ⊆-max among admissible sets satisfying the subset condition
        for a in self.F.assumptions - pro_set:
            sup = self.F.closure(pro_set | {a})
            if self.F.is_admissible(sup) and all(sup.issubset(P) for P in prefs):
                return False
        return True
class _GraphExportMixin:
    def save_dot(self, path: str) -> None:
        """Write Graphviz DOT text to *path*."""
        with open(path, "w", encoding="utf8") as fh:
            fh.write(self.to_dot())

    def save_png(self, path: str) -> None:
        """
        Render a PNG via the local `dot` executable (Graphviz).
        Requires `graphviz` installed and `dot` on $PATH.
        """
        import shutil, subprocess, tempfile, os
        if shutil.which("dot") is None:
            raise ImportError("Graphviz 'dot' not found; install graphviz.")

        with tempfile.TemporaryDirectory() as tmp:
            dot_file = os.path.join(tmp, "t.dot")
            self.save_dot(dot_file)
            subprocess.check_call(["dot", "-Tpng", dot_file, "-o", path])

    def save_html(self, path: str, notebook: bool = False) -> None:
        """
        Generate an interactive HTML using *pyvis*.
        `pip install pyvis` first.
        If *notebook=True*, returns raw HTML string for Jupyter display.
        """
        try:
            from pyvis.network import Network
        except ImportError as e:
            raise ImportError("pip install pyvis") from e

        net = Network(height="600px", width="100%", directed=True)
        counter = [0]

        def add(node, parent_id=None):
            nid = counter[0]; counter[0] += 1

            def lbl(lit: Literal | None) -> str:
                if lit is None:
                    return ""
                return str(lit.payload) if lit.payload else lit.key

            if hasattr(node, "literal"):
                label  = lbl(node.literal)
                title  = label                           # hover tooltip
                shape  = "ellipse"                       # derivation node
            else:  # dialectical node
                label  = node.role.upper()
                title  = "{"+", ".join(lbl(x) for x in node.support_set)+"}"
                shape  = "box" if node.role == "pro" else "ellipse"

            net.add_node(nid, label=label, title=title, shape=shape)
            if parent_id is not None:
                net.add_edge(parent_id, nid)

            for ch in getattr(node, "children", []):
                add(ch, nid)
            if getattr(node, "child", None):
                add(node.child, nid)

        add(self.root)
        net.set_options('{"physics": {"stabilization": false}}')
        if notebook:
            return net.generate_html()
        net.write_html(path)
@dataclass
class DialecticalNode:
    role: str                       # "pro" or "opp"
    support_set: Set["Literal"]     # the set making the move
    target: "Literal | None"        # assumption being discussed (None if node just attacks a set)
    children: list["DialecticalNode"] = field(default_factory=list)

    # pretty‐print
    def pretty(self, indent: int = 0) -> str:
        def lbl(lit: Literal) -> str:
            return lit.payload if lit.payload else lit.key
        pad = "  " * indent
        who = "PRO" if self.role == "pro" else "OPP"
        tgt = f" ⇒ {lbl(self.target)}" if self.target else ""
        members = ", ".join(lbl(x) for x in sorted(self.support_set, key=lambda l: l.key))
        head = f"{pad}{who}: {{{members}}}{tgt}"
        lines = [head]
        for ch in self.children:
            lines.append(ch.pretty(indent + 1))
        return "\n".join(lines)

    # DOT export
    def to_dot(self, parent_id: int | None = None, counter: list[int] | None = None) -> str:
        if counter is None:
            counter = [0]
        my_id = counter[0]; counter[0] += 1
        label = ("PRO" if self.role == "pro" else "OPP") + r"\n{" + \
                ", ".join(x.key for x in self.support_set) + "}"
        shape = "box" if self.role == "pro" else "ellipse"
        lines = [f'  n{my_id} [shape={shape}, label="{label}"];']
        if parent_id is not None:
            lines.append(f'  n{parent_id} -> n{my_id};')
        for ch in self.children:
            lines.append(ch.to_dot(my_id, counter))
        return "\n".join(lines)


@dataclass
class DialecticalTree(_GraphExportMixin):
    root: DialecticalNode

    def pretty(self) -> str:
        return self.root.pretty()

    def to_dot(self) -> str:
        return "digraph Dialogue {\n" + self.root.to_dot() + "\n}"

@dataclass
class DerivationNode:
    literal: "Literal"
    rule: "Rule | None"                    # None for Δ-leaf
    child: "DerivationNode | None" = None  # at most one child

    # nice console view
    def pretty(self, indent: int = 0) -> str:
        pad = "  " * indent
        label = self.literal.payload if self.literal.payload else self.literal.key
        head = f"{pad}{label}"
        if self.rule:
            head += f"   ← {self.rule.body.key}"
        if self.child:
            return head + "\n" + self.child.pretty(indent + 1)
        return head

    # Graphviz-DOT export
    def to_dot(self, parent_id: int | None = None, counter: list[int] | None = None) -> str:
        if counter is None:
            counter = [0]
        my_id = counter[0]; counter[0] += 1
        escaped_key = self.literal.key.replace('"', '\\"')
        lines = [f'  n{my_id} [label="{escaped_key}"];']
        if parent_id is not None:
            lines.append(f'  n{parent_id} -> n{my_id};')
        if self.child:
            lines.append(self.child.to_dot(my_id, counter))
        return "\n".join(lines)


@dataclass
class DerivationTree(_GraphExportMixin):
    root: DerivationNode 

    def pretty(self) -> str:
        return self.root.pretty()

    def to_dot(self) -> str:
        return "digraph Derivation {\n" + self.root.to_dot() + "\n}"

class DerivationDAG(_GraphExportMixin):
    def __init__(self, trees: list["DerivationTree"]):
        self._nodes: dict[str, Literal] = {}
        self._edges: set[tuple[str, str]] = set()
        for T in trees:
            self._collect(T.root)

    # ---------------- own exporters ----------------
    def save_html(self, path: str, notebook: bool = False) -> None:
        from pyvis.network import Network

        net = Network(height="600px", width="100%", directed=True)
        for k, lit in self._nodes.items():
            label = lit.payload if lit.payload else k
            net.add_node(k, label=label)
        for u, v in self._edges:
            net.add_edge(u, v)
        net.set_options('{"physics":{"stabilization":false},"layout":{"randomSeed":42}}')
        if notebook:
            return net.generate_html()
        net.write_html(path)

    def save_png(self, path: str) -> None:
        import shutil, subprocess, tempfile, os
        if shutil.which("dot") is None:
            raise ImportError("Graphviz 'dot' not found; install graphviz.")

        with tempfile.TemporaryDirectory() as tmp:
            dot_file = os.path.join(tmp, "dag.dot")
            with open(dot_file, "w", encoding="utf8") as fh:
                fh.write(self.to_dot())
            subprocess.check_call(["dot", "-Tpng", dot_file, "-o", path])

    # ---------------- DOT --------------------------
    def to_dot(self) -> str:
        lines = ["digraph DerivationDAG {"]
        for k, lit in self._nodes.items():
            lbl = lit.payload if lit.payload else k
            lines.append(f'  "{k}" [label="{lbl}"];')
        for u, v in sorted(self._edges):
            lines.append(f'  "{u}" -> "{v}";')
        return "\n".join(lines) + "\n}"

    # ---------------- internal ---------------------
    def _collect(self, node: "DerivationNode"):
        k = node.literal.key
        self._nodes.setdefault(k, node.literal)
        if node.child:
            ck = node.child.literal.key
            self._edges.add((ck, k))
            self._collect(node.child)


class FrameworkGraph(_GraphExportMixin):
    def __init__(self, F: "BipolarABA", include_contraries: bool = False):
        self.F = F
        self.include_contraries = include_contraries

    # -------- DOT ----------
    def _escape_dot_string(self, s: str) -> str:
        """Escape special characters for DOT format."""
        # Replace problematic characters
        s = s.replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        s = s.replace('\n', '\\n')
        s = s.replace('\r', '\\r')
        s = s.replace('\t', '\\t')
        # Truncate very long strings to avoid DOT issues
        if len(s) > 100:
            s = s[:97] + "..."
        return s

    def to_dot(self) -> str:
        lines = ["digraph Framework {",
                 '  rankdir=LR;']
        # nodes
        for a in sorted(self.F.assumptions, key=lambda l: l.key):
            label = a.payload if a.payload else a.key
            escaped_key = self._escape_dot_string(a.key)
            escaped_label = self._escape_dot_string(str(label))
            if a.type == LiteralType.FACT:
                shape = "hexagon"
                color = ',color=blue,style=filled,fillcolor=lightblue'
            else:
                shape = "ellipse"
                color = ''
            lines.append(f'  "{escaped_key}" [shape={shape},label="{escaped_label}"{color}];')

        if self.include_contraries:
            for c in sorted(self.F.contrary.values(), key=lambda l: l.key):
                escaped_key = self._escape_dot_string(c.key)
                lines.append(f'  "{escaped_key}" [shape=box,style=rounded];')
        # support edges  (green)
        for body, heads in self.F._support_from.items():
            for head in heads:
                escaped_body = self._escape_dot_string(body.key)
                escaped_head = self._escape_dot_string(head.key)
                lines.append(f'  "{escaped_body}" -> "{escaped_head}" [color=green];')
        # attack edges   (red)
        for body, targets in self.F._attack_from.items():
            for β in targets:
                escaped_body = self._escape_dot_string(body.key)
                escaped_target = self._escape_dot_string(β.key)
                lines.append(f'  "{escaped_body}" -> "{escaped_target}" [color=red];')
        return "\n".join(lines) + "\n}"

    def _escape_html_string(self, s: str) -> str:
        """Escape and truncate strings for HTML/pyvis."""
        # Truncate very long strings for better performance
        if len(s) > 80:
            s = s[:77] + "..."
        # Basic HTML escaping
        s = s.replace('&', '&amp;')
        s = s.replace('<', '&lt;')
        s = s.replace('>', '&gt;')
        s = s.replace('"', '&quot;')
        s = s.replace("'", '&#x27;')
        s = s.replace('\n', ' ')
        s = s.replace('\r', ' ')
        s = s.replace('\t', ' ')
        return s

    # -------- HTML (pyvis) ----------
    def save_html(self, path: str, notebook: bool = False) -> str | None:
        from pyvis.network import Network
        
        total_nodes = len(self.F.assumptions) + (len(self.F.contrary) if self.include_contraries else 0)
        total_edges = sum(len(heads) for heads in self.F._support_from.values()) + \
                    sum(len(targets) for targets in self.F._attack_from.values())
        
        print(f"Generating visualization with {total_nodes} nodes and {total_edges} edges...")
        
        # For extremely dense graphs, use specialized settings
        if total_nodes > 50 or total_edges > 500:
            net = Network(height="900px", width="100%", directed=True, 
                        bgcolor="#FFFFFF", font_color="black")

            #net.show_buttons()
            
            physics_options = {
                "physics": {
                    "enabled": True,
                    "forceAtlas2Based": {
                        "theta": 0.5,
                        "gravitationalConstant": -500,
                        "centralGravity": 0.001,
                        "springConstant": 0.02,
                        "springLength": 250,
                        "damping": 0.09,
                        "avoidOverlap": 2
                    },
                    "maxVelocity": 50,
                    "minVelocity": 0.1,
                    "solver": "forceAtlas2Based",
                    "stabilization": {
                        "enabled": True,
                        "iterations": 2000, 
                        "updateInterval": 100,
                        "onlyDynamicEdges": False,
                        "fit": True
                    },
                    "timestep": 0.5,
                    "adaptiveTimestep": True
                },
                "layout": {
                    "randomSeed": 42,
                    "improvedLayout": True,
                    "clusterThreshold": 150,
                    "hierarchical": {
                        "enabled": False  # Set to True if you want hierarchical layout
                    }
                },
                "interaction": {
                    "hover": True,
                    "tooltipDelay": 100,
                    "hideEdgesOnDrag": True,
                    "hideEdgesOnZoom": False,
                    "navigationButtons": True,  # Add navigation controls
                    "keyboard": {
                        "enabled": True,
                        "speed": {"x": 10, "y": 10, "zoom": 0.02}
                    }
                },
                "edges": {
                    "smooth": {
                        "enabled": True,
                        "type": "continuous",
                        "roundness": 0.5
                    },
                    "width": 0.5,  # Thinner edges for less visual clutter
                    "arrows": {
                        "to": {
                            "enabled": True,
                            "scaleFactor": 0.5  # Smaller arrows
                        }
                    }
                },
                "nodes": {
                    "font": {
                        "size": 14,
                        "strokeWidth": 0,
                        "strokeColor": "#222222"
                    },
                    "borderWidth": 1,
                    "borderWidthSelected": 2
                }
            }
        else:
            net = Network(height="750px", width="100%", directed=True)
            print("Else block engaged")
            #net.show_buttons()
            physics_options = {
                "physics": {
                    "enabled": True,
                    "forceAtlas2Based": {
                        "gravitationalConstant": -30,
                        "centralGravity": 0.01,
                        "springLength": 100,
                        "springConstant": 0.08,
                        "damping": 0.4
                    },
                    "maxVelocity": 50,
                    "solver": "forceAtlas2Based",
                    "stabilization": {
                        "enabled": True,
                        "iterations": 500
                    }
                },
                "layout": {
                    "randomSeed": 42,
                    "improvedLayout": True
                },
                "interaction": {
                    "hover": True,
                    "navigationButtons": True
                }
            }

        
        # MODIFIED SECTION: Use key as label, payload as hover text
        for a in self.F.assumptions:
            # Use key (ID) directly as the displayed label
            display_label = a.key
            
            # Use payload (text) for hover tooltip, with proper HTML escaping
            hover_text = self._escape_html_string(str(a.payload)) if a.payload else a.key
            
            if a.type == LiteralType.FACT:
                net.add_node(a.key, 
                        label=display_label,
                        shape="hexagon", 
                        title=f"FACT: {hover_text}",
                        color="#00FF00",  # Bright green for facts
                        size=25,  # Larger nodes for visibility
                        font={"size": 16, "color": "white"})
            else:
                net.add_node(a.key, 
                        label=display_label,
                        shape="ellipse", 
                        title=hover_text,
                        color="#4A90E2",  # Bright blue for assumptions
                        size=25,  # Larger nodes for visibility
                        font={"size": 16, "color": "white"})

        if self.include_contraries:
            for c in self.F.contrary.values():
                display_label = c.key
                net.add_node(c.key, 
                        label=display_label, 
                        color="#FF6B6B",  # Red for contraries
                        title=c.key,
                        size=20,
                        font={"size": 14, "color": "white"})
        
        # Make edges less prominent in dense graphs
        edge_width = 0.3 if total_edges > 500 else 0.5
        edge_opacity = 0.4 if total_edges > 500 else 0.6
        
        for body, heads in self.F._support_from.items():
            for head in heads:
                net.add_edge(body.key, head.key, 
                        color={"color": "rgba(0,255,0," + str(edge_opacity) + ")", "highlight": "green"},
                        title="support", 
                        arrows="to",
                        width=edge_width)
        
        for body, targets in self.F._attack_from.items():
            for β in targets:
                net.add_edge(body.key, β.key, 
                        color={"color": "rgba(255,0,0," + str(edge_opacity) + ")", "highlight": "red"},
                        title="attack", 
                        arrows="to",
                        width=edge_width)
        
        import json
        net.set_options(json.dumps(physics_options))
        
        html = net.generate_html()
        if not notebook:
            # Find the closing body tag and inject script before it
            inject_script = """
            <script type="text/javascript">
                // Wait for network to be available
                var checkExist = setInterval(function() {
                    if (typeof network !== 'undefined') {
                        clearInterval(checkExist);
                        network.once("stabilizationIterationsDone", function() {
                            network.setOptions({ physics: false });
                        });
                    }
                }, 100);
            </script>
            </body>"""
            
            html = html.replace('</body>', inject_script)
            
            with open(path, "w", encoding="utf8") as fh:
                fh.write(html)
        else:
            return html