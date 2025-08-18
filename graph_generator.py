#!/usr/bin/env python
"""
Complete Bipolar ABA Framework Builder - All-in-One File
Modified to show literal IDs on graph with text on hover
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Set, Any, Tuple, Callable, Iterable, List
from enum import Enum
from collections import Counter, defaultdict
from itertools import combinations, permutations
from copy import deepcopy
import json
import os
import time
from aba_pkg.baba import Literal, LiteralType, Rule, BipolarABA

class EdgeClassificationParser:
    """Parse edge classification results and build Bipolar ABA framework"""
    
    def __init__(self, classification_file: str):
        self.classification_file = classification_file
        self.data = None
        self.literals = {}
        self.edges = []
        self.framework = None
        
    def load_data(self):
        """Load the classification results from JSON"""
        print(f"Loading classification results from {self.classification_file}...")
        
        with open(self.classification_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        print(f"Loaded {self.data['metadata']['total_literals']} literals")
        print(f"Loaded {self.data['metadata']['total_edges']} edges")
        
        summary = self.data['metadata']['summary']
        print("\nEdge Classification Summary:")
        print(f"  Support edges: {summary.get('support', 0)}")
        print(f"  Attack edges: {summary.get('attack', 0)}")
        print(f"  Neutral edges: {summary.get('neutral', 0)}")
        
    def parse_literals(self, fact_ids: Set[str] = None):
        """Parse literals and create Literal objects
        
        Args:
            fact_ids: Set of literal IDs that should be marked as facts
        """
        print("\nParsing literals...")
        
        if fact_ids is None:
            fact_ids = set()
        
        for lit_data in self.data['literals']:
            lit_id = lit_data['id']
            lit_text = lit_data['text']
            
            # Determine if this is a fact or assumption
            lit_type = LiteralType.FACT if lit_id in fact_ids else LiteralType.ASSUMPTION
            
            literal = Literal(
                key=lit_id,
                type=lit_type,
                payload=lit_text
            )
            
            self.literals[lit_id] = literal
            
            # DEBUG: Print first few literals to verify parsing
            if lit_id in ['a1', 'a2', 'a3']:
                print(f"DEBUG - Created Literal: key='{literal.key}', payload='{literal.payload[:50]}...'")
        
        num_facts = sum(1 for lit in self.literals.values() if lit.type == LiteralType.FACT)
        print(f"Created {len(self.literals)} Literal objects ({num_facts} facts, {len(self.literals) - num_facts} assumptions)")
        
    def parse_edges(self):
        """Parse classified edges"""
        print("\nParsing edges...")
        
        self.edges = self.data['edges']
        
        edge_counts = {'support': 0, 'attack': 0, 'neutral': 0}
        for edge in self.edges:
            edge_counts[edge['classification']] += 1
        
        print(f"Parsed {len(self.edges)} edges:")
        for edge_type, count in edge_counts.items():
            print(f"  {edge_type}: {count}")
            
    def build_framework(self, confidence_threshold: float = 0.5):
        """Build Bipolar ABA framework from parsed data"""
        print(f"\nBuilding Bipolar ABA framework (confidence threshold: {confidence_threshold})...")
        
        # DEBUG: Check what's in self.literals
        print("DEBUG - First 3 literals in self.literals:")
        for i, (lit_id, literal) in enumerate(list(self.literals.items())[:3]):
            print(f"  {i+1}. ID: '{lit_id}' -> Literal(key='{literal.key}', payload='{literal.payload[:50] if literal.payload else literal.payload}...')")
        
        assumptions = set(self.literals.values())
        rules = set()
        
        contrary = {}
        for lit_id, literal in self.literals.items():
            contrary_literal = Literal(
                key=f"¬{lit_id}",
                type=LiteralType.ASSUMPTION,
                payload=f"NOT({literal.payload})"
            )
            contrary[literal] = contrary_literal
        
        support_count = 0
        attack_count = 0
        skipped_count = 0
        
        for edge in self.edges:
            if edge['confidence'] < confidence_threshold:
                skipped_count += 1
                continue
            
            if edge['classification'] == 'neutral':
                continue
            
            source = self.literals[edge['source_id']]
            target = self.literals[edge['target_id']]
            
            if edge['classification'] == 'support':
                rule = Rule(head=target, body=source)
                rules.add(rule)
                support_count += 1
                
            elif edge['classification'] == 'attack':
                contrary_target = contrary[target]
                rule = Rule(head=contrary_target, body=source)
                rules.add(rule)
                attack_count += 1
        
        print(f"Created {len(rules)} rules:")
        print(f"  Support rules: {support_count}")
        print(f"  Attack rules: {attack_count}")
        print(f"  Skipped (low confidence): {skipped_count}")
        
        try:
            self.framework = BipolarABA(
                assumptions=assumptions,
                contrary=contrary,
                rules=rules
            )
            print("✅ Framework created successfully!")
            
            # DEBUG: Check what's in the framework
            print("DEBUG - First 3 assumptions in framework:")
            for i, a in enumerate(list(self.framework.assumptions)[:3]):
                print(f"  {i+1}. Literal(key='{a.key}', payload='{a.payload[:50] if a.payload else a.payload}...')")
                
        except Exception as e:
            print(f"❌ Error creating framework: {e}")
            raise
            
    def calculate_extensions(self, max_extensions: int = 10):
        """Calculate various extensions of the framework"""
        if not self.framework:
            print("Error: Framework not built yet")
            return
        
        print("\n" + "="*60)
        print("CALCULATING EXTENSIONS")
        print("="*60)
        
        results = {}
        
        # For large frameworks, limit the number of extensions shown
        print(f"\nNote: Showing up to {max_extensions} extensions for each semantics")
        
        # Admissible extensions
        print("\nCalculating admissible extensions...")
        try:
            start = time.time()
            admissible = self.framework.admissible_extensions()
            elapsed = time.time() - start
            results['admissible'] = admissible
            print(f"Found {len(admissible)} admissible extensions (in {elapsed:.2f}s)")
            if len(admissible) <= max_extensions:
                for i, ext in enumerate(admissible, 1):
                    print(f"  Extension {i}: {{{', '.join(lit.key for lit in ext)}}}")
            else:
                print(f"  (Showing first {max_extensions} extensions)")
                for i, ext in enumerate(admissible[:max_extensions], 1):
                    print(f"  Extension {i}: {{{', '.join(lit.key for lit in ext)}}}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Preferred extensions
        print("\nCalculating preferred extensions...")
        try:
            start = time.time()
            preferred = self.framework.preferred_extensions()
            elapsed = time.time() - start
            results['preferred'] = preferred
            print(f"Found {len(preferred)} preferred extensions (in {elapsed:.2f}s)")
            for i, ext in enumerate(preferred[:max_extensions], 1):
                print(f"  Extension {i}: {{{', '.join(lit.key for lit in ext)}}}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Complete extensions
        print("\nCalculating complete extensions...")
        try:
            start = time.time()
            complete = self.framework.complete_extensions()
            elapsed = time.time() - start
            results['complete'] = complete
            print(f"Found {len(complete)} complete extensions (in {elapsed:.2f}s)")
            if len(complete) <= max_extensions:
                for i, ext in enumerate(complete, 1):
                    print(f"  Extension {i}: {{{', '.join(lit.key for lit in ext)}}}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Well-founded extension
        print("\nCalculating well-founded extension...")
        try:
            start = time.time()
            wf = self.framework.well_founded_extension()
            elapsed = time.time() - start
            results['well_founded'] = wf
            if wf is not None:
                print(f"Well-founded extension ({elapsed:.2f}s): {{{', '.join(lit.key for lit in wf)}}}")
            else:
                print("No well-founded extension found")
        except Exception as e:
            print(f"  Error: {e}")
        
        return results
    
    def visualize_framework(self, output_dir: str = "./visualizations", layout_type: str = "auto"):
        """Generate visualizations - HTML and PNG first
        
        Args:
            output_dir: Directory for output files
            layout_type: 'auto', 'hierarchical', or 'circular' for dense graphs
        """
        if not self.framework:
            print("Error: Framework not built yet")
            return
        
        print(f"\nGenerating visualizations in {output_dir}...")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Check graph density
        num_nodes = len(self.framework.assumptions)
        num_edges = len(self.framework.rules)
        edge_density = num_edges / (num_nodes * (num_nodes - 1) / 2) if num_nodes > 1 else 0
        
        print(f"Graph statistics: {num_nodes} nodes, {num_edges} edges")
        print(f"Edge density: {edge_density:.2%}")
        
        if edge_density > 0.3 and layout_type == "auto":
            print("⚠️  Very dense graph detected! Consider using --layout hierarchical or --layout circular")
            print("   for better visualization, or manually arrange nodes after loading.")
        
        graph = self.framework.graph(include_contraries=False)
        
        # Save HTML first
        html_file = os.path.join(output_dir, "framework.html")
        try:
            if hasattr(graph, 'layout_type'):
                graph.layout_type = layout_type
            graph.save_html(html_file)
            print(f"✅ Saved interactive HTML: {html_file}")
            print(f"   Open in browser: file://{os.path.abspath(html_file)}")
            print(f"   Tip: Use the physics toggle button to enable/disable physics simulation")
        except ImportError:
            print("⚠️  Could not save HTML (install pyvis: pip install pyvis)")
        except Exception as e:
            print(f"❌ Error saving HTML: {e}")
        
        # # Save PNG second
        # png_file = os.path.join(output_dir, "framework.png")
        # try:
        #     graph.save_png(png_file)
        #     print(f"✅ Saved PNG file: {png_file}")
        # except Exception as e:
        #     print(f"⚠️  Could not save PNG (Graphviz not installed?): {e}")
        
        # # Save DOT last
        # dot_file = os.path.join(output_dir, "framework.dot")
        # try:
        #     graph.save_dot(dot_file)
        #     print(f"✅ Saved DOT file: {dot_file}")
        # except Exception as e:
        #     print(f"❌ Error saving DOT: {e}")
        # PNG and DOT file are commented out due to performance 
        
    def save_framework_data(self, output_file: str = "./intermediate_files/bipolar_framework.json"):
        """Save framework data to JSON"""
        if not self.framework:
            print("Error: Framework not built yet")
            return
        
        print(f"\nSaving framework data to {output_file}...")
        
        framework_data = {
            'metadata': {
                'num_assumptions': len(self.framework.assumptions),
                'num_rules': len(self.framework.rules),
                'num_facts': sum(1 for a in self.framework.assumptions if a.type == LiteralType.FACT),
                'source_file': self.classification_file
            },
            'assumptions': [
                {
                    'key': lit.key,
                    'type': lit.type.value,
                    'payload': lit.payload
                }
                for lit in self.framework.assumptions
            ],
            'rules': [
                {
                    'head': rule.head.key,
                    'body': rule.body.key,
                    'type': 'support' if rule.head in self.framework.assumptions else 'attack'
                }
                for rule in self.framework.rules
            ],
            'contrary_mapping': {
                k.key: v.key for k, v in self.framework.contrary.items()
            }
        }
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(framework_data, f, indent=2)
        
        print(f"✅ Framework data saved")
    
    def run_full_pipeline(self, confidence_threshold: float = 0.5, fact_ids: Set[str] = None):
        """Run the complete pipeline"""
        print("="*60)
        print("BIPOLAR ABA FRAMEWORK BUILDER")
        print("="*60)
        
        self.load_data()
        self.parse_literals(fact_ids)
        self.parse_edges()
        self.build_framework(confidence_threshold)
        
        # Visualizations first (HTML and PNG)
        self.visualize_framework()
        
        # Then calculate extensions
        admissible_extensions = self.framework.admissible_extensions_topk(k=3)        
        # Finally save framework data
        self.save_framework_data()
        
        

        print("\n" + "="*60)
        print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*60)
        
        return admissible_extensions


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build Bipolar ABA Framework from Edge Classifications')
    parser.add_argument('--input', default='./intermediate_files/edges_classified.json',
                       help='Path to edge classification results')
    parser.add_argument('--confidence', type=float, default=0.5,
                       help='Minimum confidence threshold for edges (0-1). Higher values = fewer edges')
    parser.add_argument('--output-dir', default='./visualizations',
                       help='Directory for visualization outputs')
    parser.add_argument('--facts', nargs='*', default=[],
                       help='List of literal IDs that should be marked as facts (e.g., a1 a5 a10)')
    parser.add_argument('--layout', choices=['auto', 'hierarchical', 'circular'], default='auto',
                       help='Layout type for visualization (useful for dense graphs)')
    
    args = parser.parse_args()
    
    # Convert fact IDs to set
    fact_ids = set(args.facts) if args.facts else set()
    
    # Create parser and run pipeline
    parser = EdgeClassificationParser(args.input)
    
    try:
        # Note about confidence threshold for dense graphs
        if args.confidence == 0.5:
            print("\n💡 Tip: Your graph appears very dense. Consider using a higher confidence")
            print("   threshold (e.g., --confidence 0.7 or 0.8) to show only the strongest edges.")
            print("   This will make the visualization much more readable.\n")
        
        extensions = parser.run_full_pipeline(
            confidence_threshold=args.confidence,
            fact_ids=fact_ids
        )
        
        print("\nFinal Summary:")
        print(f"  Framework has {len(parser.framework.assumptions)} assumptions")
        print(f"  Framework has {len(parser.framework.rules)} rules")
        num_facts = sum(1 for a in parser.framework.assumptions if a.type == LiteralType.FACT)
        print(f"  Facts: {num_facts}, Assumptions: {len(parser.framework.assumptions) - num_facts}")
        
        # Edge density analysis
        num_nodes = len(parser.framework.assumptions)
        num_edges = len(parser.framework.rules)
        max_edges = num_nodes * (num_nodes - 1)
        density = (num_edges / max_edges * 100) if max_edges > 0 else 0
        
        print(f"\nGraph Density Analysis:")
        print(f"  Current edges: {num_edges}")
        print(f"  Maximum possible edges: {max_edges}")
        print(f"  Density: {density:.1f}%")
        
        if density > 30:
            print("\n⚠️  HIGH DENSITY GRAPH DETECTED!")
            print("  Recommendations for better visualization:")
            print("  1. Use higher confidence threshold: --confidence 0.7 or 0.8")
            print("  2. After opening the HTML, use the physics toggle button")
            print("  3. Manually arrange nodes by dragging them")
            print("  4. Consider focusing on specific subsets of nodes")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())