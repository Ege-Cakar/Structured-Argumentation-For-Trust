#!/usr/bin/env python
"""
Edge Classifier for your specific JSON format with sections and pre-extracted literals
"""

import json
import os
import time
import requests
from itertools import permutations
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# ===== CONFIGURATION - UPDATE THESE VALUES =====
API_KEY = os.getenv("RUNPOD_API_KEY")  
ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")  

# File paths
INPUT_FILE = "./intermediate_files/literals.json"
OUTPUT_FILE = "./intermediate_files/edges_classified.json"

# Processing settings
BATCH_SIZE = 256  # Number of edges to process at once
WINDOW_SIZE = 1   # For window mode: how many sections before/after to include (0 = same section only)
EDGE_MODE = "all"  # Options: "all" (cross-section), "same" (within section), "window" (±n sections)
# ================================================

def load_literals(filepath):
    """Load literals from your specific JSON format"""
    print(f"Loading literals from {filepath}...")
    
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        return [], []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    all_literals = []
    section_order = []  # Keep track of section ordering
    global_id_counter = 1  # Global counter for unique IDs
    
    # Your format: {section_id: {literals: {a1: "text", a2: "text"}}}
    for section_idx, (section_id, section_data) in enumerate(data.items(), 1):
        print(f"  Processing section {section_idx}: {section_id[:40]}...")
        section_order.append(section_id)  # Store section order
        
        # Get literals dictionary
        literals_dict = section_data.get('literals', {})
        num_literals = section_data.get('num_literals', 0)
        
        print(f"    Found {num_literals} literals in this section")
        
        # Convert to list format with globally unique IDs
        for original_id, lit_text in literals_dict.items():
            # Create globally unique ID
            global_unique_id = f"a{global_id_counter}"
            
            all_literals.append({
                'id': global_unique_id,  # New globally unique ID
                'text': lit_text,
                'section': section_id,
                'section_idx': section_idx - 1  # 0-based index for window calculations
            })
            global_id_counter += 1
    
    print(f"Total literals extracted: {len(all_literals)}")
    print(f"Relabeled IDs from a1 to a{global_id_counter-1}")
    return all_literals, section_order

def generate_edges(literals, section_order, mode="window", window_size=1):
    """
    Generate edges between literals with different strategies
    
    Args:
        literals: List of literal dictionaries
        section_order: Ordered list of section IDs
        mode: Edge generation mode - "all" (cross-section), "same" (within section), "window" (±n sections)
        window_size: For window mode, how many sections before/after to include
    """
    
    if mode == "all":
        # Generate all possible edges (including cross-section)
        edges = list(permutations(literals, 2))
        print(f"Generated {len(edges)} total edges (all cross-section)")
        return edges
    
    elif mode == "same":
        # Generate edges only within same section (original behavior)
        edges = []
        sections = {}
        for lit in literals:
            section = lit['section']
            if section not in sections:
                sections[section] = []
            sections[section].append(lit)
        
        for section, section_literals in sections.items():
            section_edges = list(permutations(section_literals, 2))
            edges.extend(section_edges)
            print(f"  Section {section[:30]}: {len(section_edges)} edges")
        
        print(f"Generated {len(edges)} total edges (within sections only)")
        return edges
    
    elif mode == "window":
        # Generate edges within ±window_size sections
        print(f"Generating edges with window size ±{window_size} sections")
        
        # Use a set to track unique edge IDs (to avoid duplicates)
        edge_id_set = set()
        edges = []  # Store the actual edge objects
        
        # Group literals by section index
        sections_dict = {}
        literals_by_id = {}  # Quick lookup for literals by ID
        for lit in literals:
            section_idx = lit['section_idx']
            if section_idx not in sections_dict:
                sections_dict[section_idx] = []
            sections_dict[section_idx].append(lit)
            literals_by_id[lit['id']] = lit
        
        num_sections = len(section_order)
        
        # For each section, generate edges with literals in the window
        for center_idx in range(num_sections):
            # Calculate window boundaries
            min_idx = max(0, center_idx - window_size)
            max_idx = min(num_sections - 1, center_idx + window_size)
            
            # Collect all literals in the window
            window_literals = []
            for idx in range(min_idx, max_idx + 1):
                if idx in sections_dict:
                    window_literals.extend(sections_dict[idx])
            
            # Generate all permutations within this window
            window_edges = permutations(window_literals, 2)
            
            # Add to set (using IDs as unique identifiers)
            for source, target in window_edges:
                edge_id_tuple = (source['id'], target['id'])
                if edge_id_tuple not in edge_id_set:
                    edge_id_set.add(edge_id_tuple)
                    edges.append((source, target))  # Add the actual edge
            
            print(f"  Section {center_idx} (window {min_idx}-{max_idx}): "
                  f"{len(window_literals)} literals, cumulative unique edges: {len(edges)}")
        
        print(f"Generated {len(edges)} unique edges (window size ±{window_size})")
        
        # Show statistics about cross-section edges
        cross_section_count = sum(1 for s, t in edges if s['section'] != t['section'])
        within_section_count = len(edges) - cross_section_count
        print(f"  Cross-section edges: {cross_section_count}")
        print(f"  Within-section edges: {within_section_count}")
        
        return edges
    
    else:
        raise ValueError(f"Invalid mode: {mode}. Use 'all', 'same', or 'window'")

def classify_edges_batch(edges_batch, api_key, endpoint_id):
    """Classify a batch of edges using RunPod API"""
    url = f"https://api.runpod.ai/v2/{endpoint_id}/runsync"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    pairs = []
    for source, target in edges_batch:
        pairs.append({
            "edu1": source['text'],
            "edu2": target['text']
        })
    
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
                
                classified = []
                for pred in predictions:
                    label = pred['label']
                    # Map rebuttal to attack, none to neutral
                    if label == 'rebuttal':
                        label = 'attack'
                    elif label == 'none':
                        label = 'neutral'
                    
                    classified.append({
                        'classification': label,
                        'confidence': pred['confidence'],
                        'scores': pred.get('all_scores', {})
                    })
                return classified
        
        print(f"API Error: {response.status_code}")
        return None
        
    except Exception as e:
        print(f"Error calling API: {e}")
        return None

def classify_all_edges(edges, api_key, endpoint_id, batch_size=50):
    """Classify all edges in batches"""
    classified_edges = []
    total_edges = len(edges)
    
    print(f"\nClassifying {total_edges} edges...")
    print("=" * 50)
    
    for i in range(0, total_edges, batch_size):
        batch = edges[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_edges + batch_size - 1) // batch_size
        
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} edges)...")
        
        classifications = classify_edges_batch(batch, api_key, endpoint_id)
        
        if classifications is None:
            print(f"  Warning: API failed, marking batch as neutral")
            classifications = [{'classification': 'neutral', 'confidence': 0.0, 'scores': {}} 
                            for _ in batch]
        
        for (source, target), classification in zip(batch, classifications):
            classified_edges.append({
                'source_id': source['id'],
                'source_section': source['section'][:30],
                'source_text': source['text'][:100] + '...' if len(source['text']) > 100 else source['text'],
                'target_id': target['id'],
                'target_section': target['section'][:30],
                'target_text': target['text'][:100] + '...' if len(target['text']) > 100 else target['text'],
                'cross_section': source['section'] != target['section'],
                'classification': classification['classification'],
                'confidence': classification['confidence'],
                'scores': classification.get('scores', {})
            })
        
        processed = min(i + batch_size, total_edges)
        percent = (processed / total_edges) * 100
        print(f"  Progress: {processed}/{total_edges} edges ({percent:.1f}%)")
        
        if i + batch_size < total_edges:
            time.sleep(0.5)
    
    print("=" * 50)
    return classified_edges

def save_results(classified_edges, literals, output_path, mode, window_size=None):
    """Save results to JSON file"""
    # Count classifications
    summary = {
        'total': len(classified_edges),
        'support': 0,
        'attack': 0,
        'neutral': 0,
        'cross_section_edges': 0,
        'within_section_edges': 0,
        'mode': mode,
        'window_size': window_size if mode == 'window' else None
    }
    
    # Section-wise summary
    section_summary = {}
    
    for edge in classified_edges:
        summary[edge['classification']] += 1
        
        if edge['cross_section']:
            summary['cross_section_edges'] += 1
        else:
            summary['within_section_edges'] += 1
        
        # Track per-section stats
        source_section = edge['source_section']
        if source_section not in section_summary:
            section_summary[source_section] = {'support': 0, 'attack': 0, 'neutral': 0}
        section_summary[source_section][edge['classification']] += 1
    
    # Print summary
    print("\nOverall Classification Summary:")
    print("-" * 40)
    print(f"Mode: {mode}")
    if mode == 'window':
        print(f"Window size: ±{window_size} sections")
    for cls in ['support', 'attack', 'neutral']:
        percentage = (summary[cls] / summary['total'] * 100) if summary['total'] > 0 else 0
        print(f"{cls.capitalize()}: {summary[cls]} edges ({percentage:.1f}%)")
    
    print(f"\nCross-section edges: {summary['cross_section_edges']}")
    print(f"Within-section edges: {summary['within_section_edges']}")
    
    print("\nPer-Section Summary:")
    print("-" * 40)
    for section, stats in section_summary.items():
        print(f"{section}:")
        total_section = sum(stats.values())
        for cls in ['support', 'attack', 'neutral']:
            pct = (stats[cls] / total_section * 100) if total_section > 0 else 0
            print(f"  {cls}: {stats[cls]} ({pct:.1f}%)")
    
    # Prepare output
    output = {
        'metadata': {
            'total_literals': len(literals),
            'total_edges': len(classified_edges),
            'classification_date': datetime.now().isoformat(),
            'summary': summary,
            'section_summary': section_summary
        },
        'literals': literals,
        'edges': classified_edges
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to {output_path}")

def main():
    """Main function"""
    print("Edge Classification Pipeline")
    print("=" * 50)
    
    if API_KEY == "your-runpod-api-key-here":
        print("ERROR: Please update the API_KEY in this script with your RunPod API key")
        print("Get your API key from: https://runpod.io/console/user/settings")
        return
    
    try:
        # Load literals
        literals, section_order = load_literals(INPUT_FILE)
        
        if not literals:
            print("No literals found! Check your input file format.")
            return
        
        print(f"\nFound {len(literals)} total literals across {len(section_order)} sections")
        
        # Show sample literals
        print("\nSample literals:")
        for lit in literals[:5]:
            print(f"  {lit['id']}: {lit['text'][:60]}...")
        if len(literals) > 5:
            print(f"  ... and {len(literals) - 5} more")
        
        # Edge generation based on configuration
        print("\n" + "=" * 50)
        print("Edge Generation Configuration:")
        print(f"Mode: {EDGE_MODE}")
        if EDGE_MODE == "window":
            print(f"Window size: ±{WINDOW_SIZE} sections")
        print("=" * 50)
        
        # Generate edges based on mode
        if EDGE_MODE == "all":
            edges = generate_edges(literals, section_order, mode="all")
        elif EDGE_MODE == "same":
            edges = generate_edges(literals, section_order, mode="same")
        elif EDGE_MODE == "window":
            edges = generate_edges(literals, section_order, mode="window", window_size=WINDOW_SIZE)
        else:
            print(f"Invalid EDGE_MODE: {EDGE_MODE}")
            return
        
        # Classify edges
        start_time = time.time()
        classified_edges = classify_all_edges(edges, API_KEY, ENDPOINT_ID, BATCH_SIZE)
        elapsed = time.time() - start_time
        
        print(f"\nClassification completed in {elapsed:.1f} seconds")
        print(f"Average time per edge: {elapsed/len(edges)*1000:.1f}ms")
        
        # Save results
        save_results(classified_edges, literals, OUTPUT_FILE, EDGE_MODE, 
                    WINDOW_SIZE if EDGE_MODE == "window" else None)
        
        print("\n✅ Pipeline completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
