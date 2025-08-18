#!/usr/bin/env python3
"""
Attach Fact-Logic Feedback (FL) to latest conversation checkpoint.

Changes in this version:
- No truncation by default. Full node texts are printed in the preview and in
  the appended Coordinator message.
- Added --truncate-len (default 0 = no truncation) to optionally shorten long texts.
- Support for loading _FL and _FL_N files with automatic revision numbering

Workflow
--------
1) Locate newest conversation_*_latest.json or conversation_*_FL*.json in --conv-dir.
2) Load framework analysis (prefers explicit --framework; else tries:
     ./fact_check_framework.json
     ./intermediate_files/fact_checked_framework.json).
3) Load assumption graph from ./intermediate_files/edges_classified.json (default),
   used for assumption↔assumption relations and full texts.
4) Compute:
   - fact→assumption attack chains (direct first, else one-hop via support).
   - user-requested literal defense gaps (closure vs undefended attacks).
   - "conclusion-like" literals (regex heuristic) and their defense gaps.
5) PREVIEW: print the exact Coordinator message, ask for confirmation.
6) If confirmed, append to conversation and save with incremented revision number.

Label normalization: rebuttal→attack; none/neutral→neutral.
Confidence filter: --min-confidence (default 0.575).

This is a practical graph-level approximation, not a full ABA semantics engine.
"""

from __future__ import annotations
import argparse
import json
import os
import re
import glob
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Optional, Any, Deque
from collections import defaultdict, deque

# ----------------------------
# Utility: file handling
# ----------------------------

# Updated pattern to match both _latest.json and _FL*.json files
CONV_PATTERN = re.compile(
    r"conversation_(?P<date>\d{8})_(?P<time>\d{6})_(?P<suffix>latest|FL(?:_\d+)?)\.json$"
)

def find_latest_conversation(conv_dir: str) -> str:
    """Find the most recent conversation file, including _FL and _FL_N variants."""
    candidates = []
    
    # Look for both patterns
    patterns = [
        os.path.join(conv_dir, "conversation_*_latest.json"),
        os.path.join(conv_dir, "conversation_*_FL.json"),
        os.path.join(conv_dir, "conversation_*_FL_*.json")
    ]
    
    for pattern in patterns:
        candidates.extend(glob.glob(pattern))
    
    best = None
    best_key = None
    
    for path in candidates:
        name = os.path.basename(path)
        m = CONV_PATTERN.match(name)
        if not m:
            continue
        
        # Create a sort key that considers date, time, and FL revision number
        date = m.group("date")
        time = m.group("time")
        suffix = m.group("suffix")
        
        # Extract revision number if present
        revision = 0
        if suffix.startswith("FL"):
            if "_" in suffix:
                try:
                    revision = int(suffix.split("_")[1])
                except (IndexError, ValueError):
                    pass
            elif suffix == "FL":
                revision = 0  # FL without number is treated as revision 0
        else:
            revision = -1  # 'latest' files come before FL files
        
        dt_key = (date, time, revision)
        
        if best is None or dt_key > best_key:
            best = path
            best_key = dt_key
    
    if not best:
        raise FileNotFoundError(
            f"No files matching conversation_YYYYMMDD_HHMMSS_latest.json or "
            f"conversation_YYYYMMDD_HHMMSS_FL*.json in {conv_dir}"
        )
    
    print(f"📂 Found latest conversation: {os.path.basename(best)}")
    return best

def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def derive_fl_path(original_path: str) -> str:
    """
    Derive the next FL revision path from the original path.
    - conversation_*_latest.json → conversation_*_FL.json
    - conversation_*_FL.json → conversation_*_FL_1.json
    - conversation_*_FL_N.json → conversation_*_FL_(N+1).json
    """
    dir_name = os.path.dirname(original_path)
    base_name = os.path.basename(original_path)
    
    # Check if it's already an FL file
    if "_FL" in base_name:
        # Extract the base part before _FL
        parts = base_name.split("_FL")
        base_part = parts[0]
        
        # Check if there's already a revision number
        if len(parts) > 1:
            remainder = parts[1]
            # Remove .json extension
            remainder = remainder.replace(".json", "")
            
            if remainder == "":
                # _FL.json → _FL_1.json
                new_name = f"{base_part}_FL_1.json"
            elif remainder.startswith("_"):
                # _FL_N.json → _FL_(N+1).json
                try:
                    current_rev = int(remainder[1:])
                    new_name = f"{base_part}_FL_{current_rev + 1}.json"
                except ValueError:
                    # Fallback if parsing fails
                    new_name = f"{base_part}_FL_1.json"
            else:
                # Unexpected format, default to _FL_1
                new_name = f"{base_part}_FL_1.json"
        else:
            # Shouldn't happen, but handle gracefully
            new_name = f"{base_part}_FL_1.json"
    else:
        # It's a _latest.json file, convert to _FL.json
        new_name = base_name.replace("_latest.json", "_FL.json")
    
    new_path = os.path.join(dir_name, new_name)
    print(f"📝 Will save as: {new_name}")
    return new_path

# ----------------------------
# Data structures for graph
# ----------------------------

@dataclass(frozen=True)
class Node:
    id: str
    text: str
    kind: str  # "fact" or "assumption"

class ReasoningGraph:
    """
    Lightweight reasoning graph with labeled directed edges.
    Edges are filtered by confidence >= min_conf.
    """

    def __init__(self, min_conf: float = 0.575):
        self.min_conf = min_conf
        self.nodes: Dict[str, Node] = {}
        # adjacency[label][src] = set(targets)
        self.adj: Dict[str, Dict[str, Set[str]]] = {
            "support": defaultdict(set),
            "attack": defaultdict(set),
        }
        # reverse adjacency for support closure traversal
        self.rev_support: Dict[str, Set[str]] = defaultdict(set)

    @staticmethod
    def _norm_label(label: str) -> str:
        lab = (label or "").strip().lower()
        if lab == "rebuttal":
            return "attack"
        if lab in ("none", "neutral"):
            return "neutral"
        if lab in ("support", "attack"):
            return lab
        return "neutral"

    def ensure_node(self, node_id: str, text: str, kind_hint: Optional[str] = None):
        if node_id not in self.nodes:
            kind = "fact" if (kind_hint == "fact" or node_id.startswith("fact_")) else "assumption"
            self.nodes[node_id] = Node(id=node_id, text=text or "", kind=kind)

    def add_edge(self, src: str, dst: str, label: str, confidence: float):
        lab = self._norm_label(label)
        if lab == "neutral":
            return
        if confidence is not None and confidence < self.min_conf:
            return
        if lab not in self.adj:
            return
        self.adj[lab][src].add(dst)
        if lab == "support":
            self.rev_support[dst].add(src)

    # ---------- Queries ----------

    def support_closure(self, node_id: str, limit: int = 10000) -> Set[str]:
        seen = {node_id}
        dq: Deque[str] = deque([node_id])
        while dq and len(seen) < limit:
            cur = dq.popleft()
            for pred in self.rev_support.get(cur, set()):
                if pred not in seen:
                    seen.add(pred)
                    dq.append(pred)
        return seen

    def attackers_of(self, node_id: str) -> Set[str]:
        attackers = set()
        for u, outs in self.adj["attack"].items():
            if node_id in outs:
                attackers.add(u)
        return attackers

    def attacked_by_facts_direct(self) -> Dict[str, List[str]]:
        result = defaultdict(list)
        for fact_id, outs in self.adj["attack"].items():
            if self.nodes.get(fact_id, Node(fact_id, "", "assumption")).kind == "fact":
                for tgt in outs:
                    result[tgt].append(fact_id)
        return result

    def attacked_by_facts_onehop(self) -> Dict[str, List[Tuple[str, str]]]:
        result = defaultdict(list)
        for fact_id, outs in self.adj["support"].items():
            if self.nodes.get(fact_id, Node(fact_id, "", "assumption")).kind != "fact":
                continue
            for x in outs:
                for a in self.adj["attack"].get(x, set()):
                    result[a].append((fact_id, x))
        return result

    def minimal_fact_attack_chains(self, max_per_target: int = 3) -> Dict[str, List[str]]:
        """
        Prefer direct: fact --attack--> A
        else one-hop: fact --support--> X --attack--> A
        """
        chains: Dict[str, List[str]] = defaultdict(list)
        direct = self.attacked_by_facts_direct()
        onehop = self.attacked_by_facts_onehop()

        def fmt_node(nid: str) -> str:
            n = self.nodes.get(nid, Node(nid, nid, "assumption"))
            text = " ".join((n.text or "").split())
            return f'{nid} ("{text}")'

        for a, facts in direct.items():
            for f in facts[:max_per_target]:
                chains[a].append(f"{fmt_node(f)} --attack--> {fmt_node(a)}")

        for a, pairs in onehop.items():
            remaining = max(0, max_per_target - len(chains[a]))
            for (f, x) in pairs[:remaining]:
                chains[a].append(
                    f"{fmt_node(f)} --support--> {fmt_node(x)} --attack--> {fmt_node(a)}"
                )

        return chains

    def undefended_attacks_against_closure(self, root_id: str, closure: Set[str]) -> List[Tuple[str, str]]:
        """
        For every attack U→V where V in closure, it's defended only if ∃W in closure with W→U.
        Return list of (U, V) that are NOT defended.
        """
        weaknesses: List[Tuple[str, str]] = []
        for v in closure:
            for u in self.attackers_of(v):
                defended = any(u in self.adj["attack"].get(w, set()) for w in closure)
                if not defended:
                    weaknesses.append((u, v))
        return weaknesses

# ----------------------------
# Loaders
# ----------------------------

def load_framework_any(path_hint: Optional[str]) -> Tuple[Optional[dict], str]:
    tried = []
    paths = []
    if path_hint:
        paths.append(path_hint)
    paths.append("./fact_check_framework.json")
    paths.append("./intermediate_files/fact_checked_framework.json")

    for p in paths:
        tried.append(p)
        if os.path.exists(p):
            try:
                return load_json(p), p
            except Exception as e:
                raise RuntimeError(f"Failed to load framework file {p}: {e}")

    return None, f"not found (tried: {', '.join(tried)})"

def hydrate_graph_from_files(
    graph: ReasoningGraph,
    framework_data: Optional[dict],
    edges_path: Optional[str],
) -> None:
    """
    Prefer full texts from edges_classified.literals and framework.fact_literals.
    Only fall back to (possibly truncated) source_text/target_text if needed.
    """
    # 1) edges_classified.json (assumptions + assumption edges)
    if edges_path and os.path.exists(edges_path):
        data = load_json(edges_path)
        for lit in data.get("literals", []):
            nid = lit.get("id") or lit.get("key") or ""
            text = lit.get("text") or lit.get("payload") or ""
            graph.ensure_node(nid, text, kind_hint="assumption")
        for e in data.get("edges", []):
            src = e.get("source_id")
            dst = e.get("target_id")
            cls = e.get("classification")
            conf = e.get("confidence", 0.0)
            if not (src and dst):
                continue
            # only create if missing (avoid overwriting full texts)
            if src not in graph.nodes:
                graph.ensure_node(src, e.get("source_text", ""), None)
            if dst not in graph.nodes:
                graph.ensure_node(dst, e.get("target_text", ""), None)
            graph.add_edge(src, dst, cls, conf)
    # 2) framework_data (facts + fact→assumption edges)
    if framework_data:
        for fact in framework_data.get("fact_literals", []):
            nid = fact.get("id")
            text = fact.get("text") or fact.get("payload") or ""
            if nid:
                graph.ensure_node(nid, text, kind_hint="fact")
        for fe in framework_data.get("fact_edges", []):
            src = fe.get("source_id")
            dst = fe.get("target_id")
            cls = fe.get("classification")
            conf = fe.get("confidence", 0.0)
            if not (src and dst):
                continue
            if src not in graph.nodes:
                graph.ensure_node(src, fe.get("source_text", ""), "fact")
            if dst not in graph.nodes:
                graph.ensure_node(dst, fe.get("target_text", ""), None)
            graph.add_edge(src, dst, cls, conf)

# ----------------------------
# Heuristics & formatting
# ----------------------------

CONCLUSION_REGEX = re.compile(
    r"\b(conclusion|conclude|concluding|therefore|thus|hence|ultimately|in\s+sum|in\s+summary)\b",
    flags=re.IGNORECASE,
)

def find_conclusion_like_literals(graph: ReasoningGraph, max_items: int = 20) -> List[str]:
    ids = []
    for nid, node in graph.nodes.items():
        if node.kind != "assumption":
            continue
        if node.text and CONCLUSION_REGEX.search(node.text):
            ids.append(nid)
            if len(ids) >= max_items:
                break
    return ids

def compress_whitespace(s: str) -> str:
    return " ".join((s or "").split())

def format_weakness_list(
    graph: ReasoningGraph,
    weaknesses: List[Tuple[str, str]],
    max_items: int = 10,
    truncate_len: int = 0
) -> List[str]:
    def fmt(nid: str) -> str:
        n = graph.nodes.get(nid)
        if not n:
            return nid
        t = compress_whitespace(n.text)
        if truncate_len and len(t) > truncate_len:
            t = t[:truncate_len - 1] + "…"
        return f"{nid} "{t}""
    lines = []
    for (att, v) in weaknesses[:max_items]:
        lines.append(f"- Attack not defended: {fmt(att)} → {fmt(v)}")
    return lines

def format_attack_chains(
    graph: ReasoningGraph,
    chains: Dict[str, List[str]],
    max_targets: int = 10,
    truncate_len: int = 0
) -> List[str]:
    def fmt_target(nid: str) -> str:
        n = graph.nodes.get(nid)
        t = compress_whitespace((n.text if n else "") or "")
        if truncate_len and len(t) > truncate_len:
            t = t[:truncate_len - 1] + "…"
        return f"{nid} "{t}"" if t else nid

    items = sorted(chains.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    lines = []
    for i, (target, lst) in enumerate(items[:max_targets], 1):
        lines.append(f"{i}. {fmt_target(target)}")
        if truncate_len:
            # If a truncate_len is set, we also map over the chain strings to clip inner node texts.
            mapped = []
            for c in lst:
                # best-effort: replace any "…" only if we created it (we don't mark), so we leave as-is.
                # In full mode, lst contains already-full strings, so just append.
                mapped.append(c)
            lst = mapped
        for c in lst:
            # Ensure inner strings don't contain raw newlines
            lines.append("   • " + " ".join(c.split()))
    return lines

def pick_literal_ids_by_query(graph: ReasoningGraph, raw_list: str) -> List[str]:
    wanted = []
    pool = set(graph.nodes.keys())
    tokens = [t.strip() for t in re.split(r"[,\n]", raw_list) if t.strip()]
    for t in tokens:
        if t in pool:
            wanted.append(t)
            continue
        matches = [nid for nid, n in graph.nodes.items()
                   if n.kind == "assumption" and t.lower() in (n.text or "").lower()]
        wanted.extend(matches[:5])
    seen = set()
    dedup = []
    for x in wanted:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    return dedup

# ----------------------------
# Coordinator message synthesis
# ----------------------------

def extract_revision_info(conv_path: str) -> str:
    """Extract revision information from the file path."""
    base_name = os.path.basename(conv_path)
    if "_FL_" in base_name:
        try:
            rev_num = int(base_name.split("_FL_")[1].replace(".json", ""))
            return f"Revision {rev_num}"
        except (IndexError, ValueError):
            pass
    elif "_FL" in base_name:
        return "Initial FL feedback"
    return "Initial report"

def build_coordinator_reasoning_message(
    graph: ReasoningGraph,
    min_conf: float,
    attack_chains: Dict[str, List[str]],
    user_literal_checks: List[Tuple[str, List[str]]],
    conclusion_checks: List[Tuple[str, List[str]]],
    limits: Dict[str, int],
    provenance_note: str,
    truncate_len: int = 0,
    conv_path: str = None,
) -> str:
    lines: List[str] = []
    
    # Add revision context
    revision_info = extract_revision_info(conv_path) if conv_path else ""
    
    lines.append("Decision: continue_coordinator | Reasoning: We have finished the previous report version. However, we now have a new task. I have just received auto-generated feedback from the user on our report, and we are tasked with refining and creating the next version of the report. Thus, we must go on. The feedback is attached down below.")
    
    if revision_info:
        lines.append(f"Current status: {revision_info}")
    
    lines.append("")
    lines.append("Quality caveat:")
    lines.append("- Edge matching and label predictions can be noisy; treat relationships as heuristics, not ground truth.")
    lines.append(f"- Confidence threshold applied: {min_conf:.3f}.")
    lines.append("")
    lines.append("Note: the feedback is auto-generated from the argument graph of our previous report. Thus, the feedback is simply what nodes are attacked by facts, and what nodes are undefended in said graph.")
    lines.append("Assumptions attacked by facts (minimal reasoning chains):")
    ac_lines = format_attack_chains(
        graph, attack_chains,
        max_targets=limits["attack_targets"],
        truncate_len=truncate_len
    )
    if ac_lines:
        lines.extend(ac_lines)
    else:
        lines.append("- None found at current threshold.")
    lines.append("")
    if user_literal_checks:
        lines.append("User-requested literals: unsupported or undefended points in their support-closure:")
        for (lid, weak_lines) in user_literal_checks:
            node = graph.nodes.get(lid)
            head_text = compress_whitespace((node.text if node else "") or "")
            if truncate_len and len(head_text) > truncate_len:
                head_text = head_text[:truncate_len - 1] + "…"
            head = f"{lid} "{head_text}"" if head_text else lid
            lines.append(f"- {head}")
            if weak_lines:
                for wl in weak_lines[:limits["weaknesses_per_literal"]]:
                    lines.append(f"  {wl}")
            else:
                lines.append("  ✓ No undefended attacks detected within the closure (approximate).")
        lines.append("")
    if conclusion_checks:
        lines.append("Conclusion-like literals: unsupported or undefended points. The conclusion detection uses a regex heuristic, might not be perfect:")
        for (lid, weak_lines) in conclusion_checks:
            node = graph.nodes.get(lid)
            head_text = compress_whitespace((node.text if node else "") or "")
            if truncate_len and len(head_text) > truncate_len:
                head_text = head_text[:truncate_len - 1] + "…"
            head = f"{lid} "{head_text}"" if head_text else lid
            lines.append(f"- {head}")
            if weak_lines:
                for wl in weak_lines[:limits["weaknesses_per_literal"]]:
                    lines.append(f"  {wl}")
            else:
                lines.append("  ✓ No undefended attacks detected within the closure (approximate).")
        lines.append("")
    lines.append("Now we need to:")
    lines.append("- Use the chains to tighten assumptions under direct fact pressure.")
    lines.append("- For each weakness above, either harden the premise chain (add evidence) or defend your arguments against attackers.")
    lines.append("- Prefer fixing numerical and factual errors first.")
    lines.append("- Consider if any new issues have emerged that weren't present in earlier versions.")
    return "\n".join(lines)

# ----------------------------
# Main routine
# ----------------------------

def main():
    ap = argparse.ArgumentParser(description="Attach fact-logic feedback to latest conversation checkpoint.")
    ap.add_argument("--conv-dir", default="report_generator/data/conversations", help="Directory with conversation files")
    ap.add_argument("--framework", default=None, help="Path to framework analysis JSON (fact_check_framework.json or fact_checked_framework.json)")
    ap.add_argument("--edges", default="./intermediate_files/edges_classified.json", help="Path to edges_classified.json (assumption graph)")
    ap.add_argument("--min-confidence", type=float, default=0.575, help="Minimum confidence to include edges")
    ap.add_argument("--max-items", type=int, default=10, help="Max targets to show under fact-attacks")
    ap.add_argument("--weaknesses-per-literal", type=int, default=8, help="Max weakness bullets per literal")
    ap.add_argument("--literals", default=None, help="Comma/newline-separated literal IDs or search substrings to check for support closure")
    ap.add_argument("--ask", action="store_true", help="Interactively prompt for literals to check")
    ap.add_argument("--truncate-len", type=int, default=0, help="0 = no truncation; otherwise max chars for displayed texts")
    ap.add_argument("-y", "--yes", action="store_true", help="Auto-confirm writing changes (skip prompt)")
    args = ap.parse_args()

    # 1) Locate checkpoint
    try:
        conv_path = find_latest_conversation(args.conv_dir)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return 1
    conv = load_json(conv_path)

    # 2) Load framework + edges
    framework_data, used = load_framework_any(args.framework)
    if framework_data is None:
        print(f"❌ Framework analysis file {used}. Exiting.")
        return 1

    if args.edges and not os.path.exists(args.edges):
        print(f"⚠️  No assumption-level edges found at {args.edges}.")
        print("    Direct fact→assumption attacks will still be shown; deeper chains/defense checks may be limited.")

    # 3) Build graph
    graph = ReasoningGraph(min_conf=args.min_confidence)
    hydrate_graph_from_files(graph, framework_data, args.edges)

    if not graph.nodes:
        print("❌ No nodes were loaded. Check framework and edges inputs.")
        return 1

    # 4) Fact attack chains
    chains = graph.minimal_fact_attack_chains(max_per_target=3)

    # 5) Literals to check
    wanted_ids: List[str] = []
    if args.literals:
        wanted_ids = pick_literal_ids_by_query(graph, args.literals)
    elif args.ask:
        try:
            print("\nEnter literal IDs or search terms (comma-separated), or just press Enter to skip:")
            raw = input().strip()
            if raw:
                wanted_ids = pick_literal_ids_by_query(graph, raw)
        except EOFError:
            pass

    # 6) Weaknesses for user-requested literals
    requested_weaknesses: List[Tuple[str, List[str]]] = []
    for lid in wanted_ids:
        closure = graph.support_closure(lid)
        weaknesses = graph.undefended_attacks_against_closure(lid, closure)
        formatted = format_weakness_list(
            graph, weaknesses,
            max_items=args.weaknesses_per_literal,
            truncate_len=args.truncate_len
        )
        requested_weaknesses.append((lid, formatted))

    # 7) Conclusion-like + weaknesses
    concl_ids = find_conclusion_like_literals(graph, max_items=args.max_items)
    conclusion_weaknesses: List[Tuple[str, List[str]]] = []
    for lid in concl_ids:
        closure = graph.support_closure(lid)
        weaknesses = graph.undefended_attacks_against_closure(lid, closure)
        formatted = format_weakness_list(
            graph, weaknesses,
            max_items=args.weaknesses_per_literal,
            truncate_len=args.truncate_len
        )
        conclusion_weaknesses.append((lid, formatted))

    # 8) Build coordinator message (preview only)
    message_blob = build_coordinator_reasoning_message(
        graph=graph,
        min_conf=args.min_confidence,
        attack_chains=chains,
        user_literal_checks=requested_weaknesses,
        conclusion_checks=conclusion_weaknesses,
        limits={"attack_targets": args.max_items, "weaknesses_per_literal": args.weaknesses_per_literal},
        provenance_note=used,
        truncate_len=args.truncate_len,
        conv_path=conv_path,
    )

    # 9) PREVIEW & CONFIRM
    print("\n" + "="*80)
    print("PROPOSED COORDINATOR MESSAGE (preview)")
    print("="*80)
    print(message_blob)
    print("="*80 + "\n")

    proceed = args.yes
    if not proceed:
        try:
            resp = input("Append this message to the conversation and save with incremented revision? [y/N]: ").strip().lower()
            proceed = resp in ("y", "yes")
        except EOFError:
            proceed = False

    if not proceed:
        print("Aborted. No changes written.")
        return 0

    # 10) Append and save
    coordinator_entry = {
        "speaker": "Coordinator",
        "content": message_blob
    }
    conv.setdefault("messages", []).append(coordinator_entry)
    conv["coordinator_decision"] = "continue_coordinator"
    conv["current_speaker"] = "Coordinator"
    if "message_count" in conv:
        try:
            conv["message_count"] = int(conv.get("message_count", 0)) + 1
        except Exception:
            pass

    out_path = derive_fl_path(conv_path)
    save_json(out_path, conv)
    print(f"✅ Attached fact-logic feedback and saved:")
    print(f"   {out_path}")
    print(f"   (Source checkpoint: {conv_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())