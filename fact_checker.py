import json
import os
import time
import requests
import re
from typing import Dict, Set, List, Tuple, Any
from datetime import datetime
from dotenv import load_dotenv
from itertools import product
from enum import Enum

# Import from your ABA package
from aba_pkg.baba import Literal, LiteralType, Rule, BipolarABA

load_dotenv()

# ===== CONFIGURATION =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")

# File paths
EDGES_CLASSIFIED_FILE = "./intermediate_files/edges_classified.json"
FACTS_FILE = "./initial_files/facts.md"
OUTPUT_FILE = "./intermediate_files/fact_checked_framework.json"
VISUALIZATION_DIR = "./visualizations"

# Model settings
LITERAL_EXTRACTOR_MODEL = os.getenv(
    "OPENAI_MODEL",
    "ft:gpt-4.1-mini-2025-04-14:personal:literal-extractor-mini:C2dwgR7K"
)

# Processing settings
MAX_CHUNK_SIZE = 3000  # Maximum characters per chunk for literal extraction
EDGE_BATCH_SIZE = 256  # Batch size for edge classification
CONFIDENCE_THRESHOLD = 0.575  # Minimum confidence for edge inclusion

# ===========================
def json_default(o):
    if isinstance(o, Enum):
        return o.name  # e.g., "FACT", "ASSUMPTION"
    return str(o)      # fallback

class FactChecker:
    """Main fact checking pipeline"""
    
    def __init__(self, edges_file=None, facts_file=None, output_file=None, 
                 confidence_threshold=0.575, batch_size=256):
        self.edges_file = edges_file or EDGES_CLASSIFIED_FILE
        self.facts_file = facts_file or FACTS_FILE
        self.output_file = output_file or OUTPUT_FILE
        self.confidence_threshold = confidence_threshold
        self.batch_size = batch_size
        
        self.edges_data = None
        self.existing_literals = {}
        self.fact_literals = {}
        self.fact_to_literal_edges = []
        self.classified_fact_edges = []
        self.framework = None
        
    def load_existing_graph(self):
        """Load the existing edges_classified.json data"""
        print("="*60)
        print("LOADING EXISTING GRAPH")
        print("="*60)
        
        with open(self.edges_file, 'r', encoding='utf-8') as f:
            self.edges_data = json.load(f)
        
        # Parse existing literals
        for lit_data in self.edges_data['literals']:
            lit_id = lit_data['id']
            lit_text = lit_data['text']
            
            self.existing_literals[lit_id] = {
                'id': lit_id,
                'text': lit_text,
                'section': lit_data.get('section', ''),
                'type': LiteralType.ASSUMPTION  # Existing literals are assumptions
            }
        
        print(f"Loaded {len(self.existing_literals)} existing literals")
        print(f"Loaded {len(self.edges_data['edges'])} existing edges")
        
    def segment_facts_file(self, filepath: str) -> List[Dict[str, str]]:
        """Segment facts.md file into processable chunks"""
        print("\n" + "="*60)
        print("SEGMENTING FACTS FILE")
        print("="*60)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        segments = []
        
        # Split by headers (##, ###, etc.)
        header_pattern = r'^#{2,}\s+(.+)$'
        
        # First, try to split by major sections
        sections = re.split(r'^##\s+', content, flags=re.MULTILINE)
        
        for section in sections:
            if not section.strip():
                continue
                
            # Check if section is too long
            if len(section) > MAX_CHUNK_SIZE:
                # Further split by subsections or paragraphs
                subsections = re.split(r'^###\s+', section, flags=re.MULTILINE)
                
                for subsection in subsections:
                    if not subsection.strip():
                        continue
                        
                    if len(subsection) > MAX_CHUNK_SIZE:
                        # Split into paragraphs
                        paragraphs = subsection.split('\n\n')
                        current_chunk = ""
                        
                        for para in paragraphs:
                            if len(current_chunk) + len(para) < MAX_CHUNK_SIZE:
                                current_chunk += para + "\n\n"
                            else:
                                if current_chunk:
                                    segments.append({
                                        'text': current_chunk.strip(),
                                        'source': 'facts'
                                    })
                                current_chunk = para + "\n\n"
                        
                        if current_chunk:
                            segments.append({
                                'text': current_chunk.strip(),
                                'source': 'facts'
                            })
                    else:
                        segments.append({
                            'text': subsection.strip(),
                            'source': 'facts'
                        })
            else:
                segments.append({
                    'text': section.strip(),
                    'source': 'facts'
                })
        
        print(f"Segmented facts into {len(segments)} chunks")
        for i, seg in enumerate(segments[:3], 1):
            preview = seg['text'][:100] + "..." if len(seg['text']) > 100 else seg['text']
            print(f"  Chunk {i}: {preview}")
        
        return segments
    
    def extract_fact_literals(self, segments: List[Dict[str, str]]):
        """Extract literals from fact segments using OpenAI API"""
        print("\n" + "="*60)
        print("EXTRACTING FACT LITERALS")
        print("="*60)
        
        if not OPENAI_API_KEY:
            print("ERROR: OPENAI_API_KEY not set")
            return
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
        except ImportError:
            print("ERROR: OpenAI package not installed. Run: pip install openai")
            return
        
        system_prompt = (
            "You are an fact extraction assistant. Given a text containing historical facts and data, "
            "identify each factual statement as a separate component. Focus on specific, verifiable facts "
            "like dates, numbers, names, and events. Return exactly this JSON:\n"
            "{\n"
            "  \"literals\": {\n"
            "    \"f1\": \"<first fact>\",\n"
            "    \"f2\": \"<second fact>\",\n"
            "    ...\n"
            "  }\n"
            "}\n"
            "Number the keys (f1, f2, ...) in order of appearance. Extract concrete, atomic facts."
        )
        
        fact_counter = 1
        
        for seg_idx, segment in enumerate(segments, 1):
            print(f"Processing segment {seg_idx}/{len(segments)}...")
            
            try:
                response = client.chat.completions.create(
                    model=LITERAL_EXTRACTOR_MODEL,
                    temperature=0,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": segment['text']}
                    ]
                )
                
                content = response.choices[0].message.content or ""
                
                # Parse the response
                literals_dict = self._parse_literals_response(content)
                
                # Add to fact_literals with global numbering
                for local_key, fact_text in literals_dict.items():
                    global_fact_id = f"fact_{fact_counter}"
                    self.fact_literals[global_fact_id] = {
                        'id': global_fact_id,
                        'text': fact_text,
                        'source': f"facts_segment_{seg_idx}",
                        'type': LiteralType.FACT
                    }
                    fact_counter += 1
                
                print(f"  Extracted {len(literals_dict)} facts from segment {seg_idx}")
                
            except Exception as e:
                print(f"  ERROR extracting from segment {seg_idx}: {e}")
                continue
        
        print(f"\nTotal facts extracted: {len(self.fact_literals)}")
        
        # Show sample facts
        if self.fact_literals:
            print("\n" + "="*60)
            print("EXTRACTED FACTS (FULL LIST)")
            print("="*60)
            for i, (fact_id, fact_data) in enumerate(self.fact_literals.items(), 1):
                print(f"\n{i}. {fact_id}:")
                print(f"   {fact_data['text']}")
            print("="*60)
            
            # Ask for confirmation to proceed
            print(f"\n✓ Extracted {len(self.fact_literals)} facts from the document")
            print("These facts will be checked against existing literals for relationships.")
            input("Press Enter to continue with edge generation and classification...")

    
    def _parse_literals_response(self, response_text: str) -> Dict[str, str]:
        """Parse the OpenAI response to extract literals dictionary"""
        response_text = response_text.strip()
        
        # Try direct JSON parsing
        try:
            parsed = json.loads(response_text)
            literals = parsed.get('literals', {})
            if isinstance(literals, dict):
                return literals
        except:
            pass
        
        # Try to extract JSON object
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                literals = parsed.get('literals', {})
                if isinstance(literals, dict):
                    return literals
            except:
                pass
        
        return {}
    
    def generate_fact_edges(self):
        """Generate edges FROM facts TO existing literals"""
        print("\n" + "="*60)
        print("GENERATING FACT EDGES")
        print("="*60)
        
        # Create all possible edges from facts to existing literals
        self.fact_to_literal_edges = []
        
        for fact_id, fact_data in self.fact_literals.items():
            for lit_id, lit_data in self.existing_literals.items():
                edge = {
                    'source': fact_data,
                    'target': lit_data
                }
                self.fact_to_literal_edges.append(edge)
        
        print(f"Generated {len(self.fact_to_literal_edges)} potential edges")
        print(f"  ({len(self.fact_literals)} facts × {len(self.existing_literals)} literals)")
    
    def classify_fact_edges(self):
        """Classify fact-to-literal edges using RunPod API"""
        print("\n" + "="*60)
        print("CLASSIFYING FACT EDGES")
        print("="*60)
        
        if not RUNPOD_API_KEY or not RUNPOD_ENDPOINT_ID:
            print("ERROR: RunPod credentials not set")
            return
        
        total_edges = len(self.fact_to_literal_edges)
        print(f"Classifying {total_edges} edges in batches of {EDGE_BATCH_SIZE}...")
        
        for i in range(0, total_edges, EDGE_BATCH_SIZE):
            batch = self.fact_to_literal_edges[i:i + EDGE_BATCH_SIZE]
            batch_num = (i // EDGE_BATCH_SIZE) + 1
            total_batches = (total_edges + EDGE_BATCH_SIZE - 1) // EDGE_BATCH_SIZE
            
            print(f"Processing batch {batch_num}/{total_batches}...")
            
            # Prepare batch for API
            pairs = []
            for edge in batch:
                pairs.append({
                    "edu1": edge['source']['text'],
                    "edu2": edge['target']['text']
                })
            
            # Call API
            classifications = self._call_runpod_api(pairs)
            
            if classifications is None:
                print(f"  Warning: API failed, marking batch as neutral")
                classifications = [{'classification': 'neutral', 'confidence': 0.0} for _ in batch]
            
            # Store classified edges
            for edge, classification in zip(batch, classifications):
                self.classified_fact_edges.append({
                    'source_id': edge['source']['id'],
                    'source_text': edge['source']['text'][:100] + '...',
                    'target_id': edge['target']['id'],
                    'target_text': edge['target']['text'][:100] + '...',
                    'classification': classification['classification'],
                    'confidence': classification['confidence'],
                    'is_fact_edge': True
                })
            
            progress = min(i + EDGE_BATCH_SIZE, total_edges)
            print(f"  Progress: {progress}/{total_edges} ({progress*100/total_edges:.1f}%)")
            
            if i + EDGE_BATCH_SIZE < total_edges:
                time.sleep(0.5)  # Rate limiting
        
        # Summary
        summary = {'support': 0, 'attack': 0, 'neutral': 0}
        for edge in self.classified_fact_edges:
            if edge['classification'] == 'rebuttal':
                edge['classification'] = 'attack'  # Normalize
            summary[edge['classification']] += 1
        
        print("\nFact Edge Classification Summary:")
        for cls, count in summary.items():
            pct = (count / len(self.classified_fact_edges) * 100) if self.classified_fact_edges else 0
            print(f"  {cls}: {count} ({pct:.1f}%)")
    
    def _call_runpod_api(self, pairs: List[Dict]) -> List[Dict]:
        """Call RunPod API for edge classification"""
        url = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/runsync"
        headers = {
            "Authorization": f"Bearer {RUNPOD_API_KEY}",
            "Content-Type": "application/json"
        }
        
        request_data = {
            "input": {
                "pairs": pairs,
                "return_all_scores": True
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=request_data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'COMPLETED':
                    predictions = result.get('output', {}).get('predictions', [])
                    
                    # Transform the predictions to match expected format
                    classified = []
                    for pred in predictions:
                        label = pred.get('label', 'neutral')
                        # Normalize labels
                        if label == 'rebuttal':
                            label = 'attack'
                        elif label == 'none':
                            label = 'neutral'
                        
                        classified.append({
                            'classification': label,
                            'confidence': pred.get('confidence', 0.0),
                            'scores': pred.get('all_scores', {})
                        })
                    return classified
            
            return None
            
        except Exception as e:
            print(f"  API Error: {e}")
            return None
    
    def build_enhanced_framework(self):
        """Build Bipolar ABA framework with fact nodes and edges"""
        print("\n" + "="*60)
        print("BUILDING ENHANCED FRAMEWORK")
        print("="*60)
        
        # Create all literals (existing + facts)
        all_literals = {}
        
        # Add existing literals as assumptions
        for lit_id, lit_data in self.existing_literals.items():
            literal = Literal(
                key=lit_id,
                type=LiteralType.ASSUMPTION,
                payload=lit_data['text']
            )
            all_literals[lit_id] = literal
        
        # Add fact literals as facts
        for fact_id, fact_data in self.fact_literals.items():
            literal = Literal(
                key=fact_id,
                type=LiteralType.FACT,
                payload=fact_data['text']
            )
            all_literals[fact_id] = literal
        
        print(f"Created {len(all_literals)} total literals")
        print(f"  Assumptions: {len(self.existing_literals)}")
        print(f"  Facts: {len(self.fact_literals)}")
        
        # Build assumptions set (includes both types for framework construction)
        assumptions = set(all_literals.values())
        
        # Create contrary mapping
        contrary = {}
        for lit_id, literal in all_literals.items():
            contrary_literal = Literal(
                key=f"¬{lit_id}",
                type=LiteralType.ASSUMPTION,
                payload=f"NOT({literal.payload})"
            )
            contrary[literal] = contrary_literal
        
        # Build rules from edges
        rules = set()
        
        # Add existing edges
        existing_strong_edges = 0
        for edge in self.edges_data['edges']:
            if edge['confidence'] < CONFIDENCE_THRESHOLD:
                continue
            
            if edge['classification'] == 'neutral':
                continue
            
            source = all_literals[edge['source_id']]
            target = all_literals[edge['target_id']]
            
            if edge['classification'] == 'support':
                rule = Rule(head=target, body=source)
                rules.add(rule)
                existing_strong_edges += 1
            elif edge['classification'] in ['attack', 'rebuttal']:
                contrary_target = contrary[target]
                rule = Rule(head=contrary_target, body=source)
                rules.add(rule)
                existing_strong_edges += 1
        
        print(f"Added {existing_strong_edges} existing edges (threshold: {CONFIDENCE_THRESHOLD})")
        
        # Add fact edges (only FROM facts TO assumptions)
        fact_strong_edges = 0
        for edge in self.classified_fact_edges:
            if edge['confidence'] < CONFIDENCE_THRESHOLD:
                continue
            
            if edge['classification'] == 'neutral':
                continue
            
            source = all_literals[edge['source_id']]
            target = all_literals[edge['target_id']]
            
            if edge['classification'] == 'support':
                rule = Rule(head=target, body=source)
                rules.add(rule)
                fact_strong_edges += 1
            elif edge['classification'] in ['attack', 'rebuttal']:
                contrary_target = contrary[target]
                rule = Rule(head=contrary_target, body=source)
                rules.add(rule)
                fact_strong_edges += 1
        
        print(f"Added {fact_strong_edges} fact edges (threshold: {CONFIDENCE_THRESHOLD})")
        print(f"Total rules in framework: {len(rules)}")
        
        # Create framework
        try:
            self.framework = BipolarABA(
                assumptions=assumptions,
                contrary=contrary,
                rules=rules
            )
            print("✅ Enhanced framework created successfully!")
            print("\n" + "="*60)
            print("ANALYZING FACT-BASED ATTACKS")
            print("="*60)
            self.framework.print_fact_attacks()
            
        except Exception as e:
            print(f"❌ Error creating framework: {e}")
            raise
    
    def visualize_framework(self):
        """Generate HTML visualization of the enhanced framework"""
        print("\n" + "="*60)
        print("VISUALIZING ENHANCED FRAMEWORK")
        print("="*60)
        
        if not self.framework:
            print("ERROR: Framework not built yet")
            return
        
        os.makedirs(VISUALIZATION_DIR, exist_ok=True)
        
        # Get graph statistics
        num_nodes = len(self.framework.assumptions)
        num_rules = len(self.framework.rules)
        num_facts = sum(1 for a in self.framework.assumptions if a.type == LiteralType.FACT)
        
        print(f"Graph statistics:")
        print(f"  Total nodes: {num_nodes}")
        print(f"  Facts: {num_facts}")
        print(f"  Assumptions: {num_nodes - num_facts}")
        print(f"  Total edges: {num_rules}")
        
        # Generate visualization
        graph = self.framework.graph(include_contraries=False)
        html_file = os.path.join(VISUALIZATION_DIR, "fact_checked_framework.html")
        
        try:
            graph.save_html(html_file)
            print(f"✅ Saved interactive HTML: {html_file}")
            print(f"   Open in browser: file://{os.path.abspath(html_file)}")
            print(f"   Tip: Green nodes are facts, blue nodes are assumptions")
        except Exception as e:
            print(f"❌ Error saving visualization: {e}")
    
    def calculate_extensions(self, max_extensions: int = 10):
        """Calculate extensions of the enhanced framework"""
        print("\n" + "="*60)
        print("CALCULATING EXTENSIONS")
        print("="*60)
        
        if not self.framework:
            print("ERROR: Framework not built yet")
            return
        
        print(f"Note: Showing up to {max_extensions} extensions for each semantics\n")
        
        # Well-founded extension (fastest)
        print("Calculating well-founded extension...")
        try:
            start = time.time()
            wf = self.framework.well_founded_extension()
            elapsed = time.time() - start
            if wf is not None:
                fact_count = sum(1 for lit in wf if lit.key.startswith('fact_'))
                print(f"Well-founded extension ({elapsed:.2f}s):")
                print(f"  Size: {len(wf)} literals ({fact_count} facts)")
                if len(wf) <= 20:
                    print(f"  Members: {{{', '.join(lit.key for lit in wf)}}}")
            else:
                print("No well-founded extension found")
        except Exception as e:
            print(f"  Error: {e}")
        
        # For large frameworks, skip expensive computations
        if len(self.framework.assumptions) > 100:
            print("\n⚠️  Framework too large for complete extension computation")
            print("  (Would require exponential time)")
            return
        
        # Preferred extensions
        print("\nCalculating preferred extensions...")
        try:
            start = time.time()
            preferred = self.framework.preferred_extensions()
            elapsed = time.time() - start
            print(f"Found {len(preferred)} preferred extensions (in {elapsed:.2f}s)")
            for i, ext in enumerate(preferred[:max_extensions], 1):
                fact_count = sum(1 for lit in ext if lit.key.startswith('fact_'))
                print(f"  Extension {i}: {len(ext)} literals ({fact_count} facts)")
        except Exception as e:
            print(f"  Error: {e}")
    
    def save_results(self):
        """Save the enhanced framework data to JSON"""
        print("\n" + "="*60)
        print("SAVING RESULTS")
        print("="*60)
        
        output_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'num_existing_literals': len(self.existing_literals),
                'num_fact_literals': len(self.fact_literals),
                'num_fact_edges': len(self.classified_fact_edges),
                'confidence_threshold': CONFIDENCE_THRESHOLD
            },
            'fact_literals': list(self.fact_literals.values()),
            'fact_edges': self.classified_fact_edges,
            'framework_stats': {
                'total_assumptions': len(self.framework.assumptions) if self.framework else 0,
                'total_rules': len(self.framework.rules) if self.framework else 0,
                'num_facts': sum(1 for a in self.framework.assumptions if a.type == LiteralType.FACT) if self.framework else 0
            }
        }
        
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, default=json_default)
        
        print(f"✅ Results saved to {OUTPUT_FILE}")
    
    def run_pipeline(self):
        """Run the complete fact-checking pipeline"""
        print("="*60)
        print("FACT CHECKING PIPELINE")
        print("="*60)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Step 1: Load existing graph
            self.load_existing_graph()
            
            # Step 2: Process facts file
            if not os.path.exists(FACTS_FILE):
                print(f"\n❌ Facts file not found: {FACTS_FILE}")
                print("Please create a facts.md file with historical facts to check")
                return
            
            segments = self.segment_facts_file(FACTS_FILE)
            
            # Step 3: Extract fact literals
            self.extract_fact_literals(segments)
            
            if not self.fact_literals:
                print("\n❌ No facts extracted. Check your facts file and API key.")
                return
            
            # Step 4: Generate edges from facts to literals
            self.generate_fact_edges()
            
            # Step 5: Classify fact edges
            self.classify_fact_edges()
            
            # Step 6: Build enhanced framework
            self.build_enhanced_framework()
            
            # Step 7: Visualize
            self.visualize_framework()
            
            # Step 8: Save results
            self.save_results()
            
            # Step 9: Calculate extensions
            admissible_extensions = self.framework.admissible_extensions_topk(k=3)   

            def _exts_to_keys(exts):
                return [sorted(l.key for l in ext) for ext in exts]

            ext_keysets = _exts_to_keys(admissible_extensions)
            sizes = [len(ext) for ext in admissible_extensions]

            print("\nTop-k admissible extensions (by size):", sizes)
            for i, keys in enumerate(ext_keysets, 1):
                sample = ", ".join(keys[:12])
                print(f"  #{i}: |Δ|={len(keys)}   sample=[{sample}{'...' if len(keys) > 12 else ''}]")

            out_path = "./intermediate_files/topk_admissible.json"
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            payloads = {a.key: (a.payload if isinstance(a.payload, str) else str(a.payload))
                        for a in self.framework.assumptions}
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "k": len(ext_keysets),
                        "sizes": sizes,
                        "extensions": ext_keysets,  # lists of literal IDs
                        "payloads": payloads        # id -> text lookup
                    },
                    f,
                    indent=2
                )
            print(f"✅ Saved top-k admissible extensions → {out_path}")

            print("\n" + "="*60)
            print("✅ FACT CHECKING PIPELINE COMPLETED!")
            print("="*60)
            
            # Final summary
            print("\nFinal Summary:")
            print(f"  Original literals: {len(self.existing_literals)}")
            print(f"  Fact literals added: {len(self.fact_literals)}")
            print(f"  Fact edges classified: {len(self.classified_fact_edges)}")
            
            # Count significant edges
            significant_facts = sum(1 for e in self.classified_fact_edges 
                                   if e['confidence'] >= CONFIDENCE_THRESHOLD 
                                   and e['classification'] != 'neutral')
            print(f"  Significant fact relationships: {significant_facts}")
            
            print(f"\nVisualization available at:")
            print(f"  file://{os.path.abspath(os.path.join(VISUALIZATION_DIR, 'fact_checked_framework.html'))}")
            
        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fact Checker for Bipolar ABA Framework')
    parser.add_argument('--edges-file', default='./intermediate_files/edges_classified.json',
                       help='Path to edges_classified.json')
    parser.add_argument('--facts-file', default='./initial_files/facts.md',
                       help='Path to facts.md file')
    parser.add_argument('--confidence', type=float, default=0.5,
                       help='Minimum confidence threshold for edges')
    parser.add_argument('--batch-size', type=int, default=256,
                       help='Batch size for edge classification')
    parser.add_argument('--output', default='./intermediate_files/fact_checked_framework.json',
                       help='Output file path')
    
    args = parser.parse_args()
    
    # Check required files
    if not os.path.exists(args.edges_file):
        print(f"ERROR: Edges file not found: {args.edges_file}")
        print("Please run edge_classifier.py first to generate edges_classified.json")
        return 1
    
    if not os.path.exists(args.facts_file):
        print(f"ERROR: Facts file not found: {args.facts_file}")
        print("Please create a facts.md file with historical facts to check")
        return 1
    
    # Check API keys
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set in environment")
        print("Please set your OpenAI API key in .env file")
        return 1
    
    if not RUNPOD_API_KEY or not RUNPOD_ENDPOINT_ID:
        print("WARNING: RunPod credentials not set")
        print("Edge classification will fail. Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in .env")
    
    # Create checker with actual command line arguments
    checker = FactChecker(
        edges_file=args.edges_file,
        facts_file=args.facts_file,
        output_file=args.output,
        confidence_threshold=args.confidence,
        batch_size=args.batch_size
    )
    checker.run_pipeline()
    
    return 0

if __name__ == "__main__":
    exit(main())