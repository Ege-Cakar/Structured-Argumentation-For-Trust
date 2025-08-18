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
CHECKPOINT_FILE = "./intermediate_files/checkpoint.json"  # For resume functionality
PARTIAL_RESULTS_FILE = "./intermediate_files/edges_classified_partial.jsonl"  # Incremental results

# Processing settings
BATCH_SIZE = 256  # Number of edges to process at once
WINDOW_SIZE = 1   # For window mode: how many sections before/after to include (0 = same section only)
EDGE_MODE = "all"  # Options: "all" (cross-section), "same" (within section), "window" (±n sections)

# Checkpoint settings
CHECKPOINT_FREQUENCY = 50  # Save checkpoint every N batches (adjust based on your needs)
INCREMENTAL_SAVE = True  # If True, saves results incrementally to avoid huge memory usage

# Retry settings
MAX_RETRIES = 3  # Maximum number of retries for failed API calls
RETRY_DELAY = 2  # Initial delay in seconds between retries (will be exponentially increased)
# ================================================

def load_checkpoint():
    """Load checkpoint if it exists"""
    # First check for old pickle checkpoint
    old_pickle_file = "./intermediate_files/checkpoint.pkl"
    if os.path.exists(old_pickle_file):
        print(f"Found old pickle checkpoint at {old_pickle_file}")
        try:
            import pickle
            with open(old_pickle_file, 'rb') as f:
                checkpoint = pickle.load(f)
            
            # Check if this is an old-style checkpoint with all edges included
            if 'classified_edges' in checkpoint and checkpoint['classified_edges']:
                num_edges = len(checkpoint['classified_edges'])
                if INCREMENTAL_SAVE and num_edges > 0:
                    print(f"\n⚠️  Detected old pickle checkpoint with {num_edges} edges.")
                    print("Migrating to new format...")
                    
                    # Migrate edges to incremental file
                    migrate_to_incremental(checkpoint['classified_edges'])
                    checkpoint['edges_processed_count'] = num_edges
                    checkpoint['classified_edges'] = []
                    
                    # Save as JSON and delete old pickle
                    save_checkpoint(checkpoint, force=True)
                    os.remove(old_pickle_file)
                    print("✓ Migration complete! Old pickle file deleted.")
            else:
                # Convert pickle checkpoint to JSON
                save_checkpoint(checkpoint, force=True)
                os.remove(old_pickle_file)
                print("✓ Converted checkpoint from pickle to JSON format")
            
            print(f"Resuming from batch {checkpoint['last_completed_batch'] + 1}")
            return checkpoint
        except Exception as e:
            print(f"Error loading old pickle checkpoint: {e}")
            print("Starting fresh...")
            return None
    
    # Load JSON checkpoint
    if os.path.exists(CHECKPOINT_FILE):
        print(f"Found checkpoint file at {CHECKPOINT_FILE}")
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                checkpoint = json.load(f)
            
            print(f"Resuming from batch {checkpoint['last_completed_batch'] + 1}")
            return checkpoint
        except Exception as e:
            print(f"Error loading checkpoint: {e}")
            print("Starting fresh...")
            return None
    return None

def migrate_to_incremental(classified_edges):
    """Migrate classified edges from old checkpoint format to incremental file"""
    try:
        os.makedirs(os.path.dirname(PARTIAL_RESULTS_FILE), exist_ok=True)
        print(f"  Writing {len(classified_edges)} edges to {PARTIAL_RESULTS_FILE}...")
        
        with open(PARTIAL_RESULTS_FILE, 'w') as f:
            for i, edge in enumerate(classified_edges):
                f.write(json.dumps(edge) + '\n')
                if (i + 1) % 10000 == 0:
                    print(f"    Migrated {i + 1}/{len(classified_edges)} edges...")
        
        print(f"  ✓ Successfully migrated all edges to incremental file")
    except Exception as e:
        print(f"  ❌ Error during migration: {e}")
        raise

def save_checkpoint(checkpoint_data, force=False):
    """Save checkpoint to JSON file (only at intervals unless forced)"""
    batch_num = checkpoint_data['last_completed_batch'] + 1
    
    # Only save at checkpoint frequency or when forced
    if not force and batch_num % CHECKPOINT_FREQUENCY != 0:
        return
    
    try:
        os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
        
        # Always save minimal checkpoint (no edges) when using incremental save
        checkpoint_to_save = {
            'last_completed_batch': checkpoint_data['last_completed_batch'],
            'total_edges': checkpoint_data['total_edges'],
            'edge_mode': checkpoint_data['edge_mode'],
            'window_size': checkpoint_data.get('window_size'),
            'edges_processed_count': checkpoint_data.get('edges_processed_count', 0)
        }
        
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint_to_save, f, indent=2)
        
        print(f"  ✓ Checkpoint saved at batch {batch_num}")
    except Exception as e:
        print(f"  Warning: Could not save checkpoint: {e}")

def save_incremental_results(edges_batch):
    """Save classified edges incrementally to avoid memory issues"""
    if not INCREMENTAL_SAVE:
        return
    
    try:
        os.makedirs(os.path.dirname(PARTIAL_RESULTS_FILE), exist_ok=True)
        with open(PARTIAL_RESULTS_FILE, 'a') as f:
            for edge in edges_batch:
                f.write(json.dumps(edge) + '\n')
    except Exception as e:
        print(f"  Warning: Could not save incremental results: {e}")

def load_incremental_results():
    """Load previously saved incremental results"""
    if not os.path.exists(PARTIAL_RESULTS_FILE):
        return []
    
    edges = []
    try:
        with open(PARTIAL_RESULTS_FILE, 'r') as f:
            for line in f:
                edges.append(json.loads(line))
        print(f"Loaded {len(edges)} previously classified edges from incremental file")
        return edges
    except Exception as e:
        print(f"Warning: Could not load incremental results: {e}")
        return []

def delete_checkpoint():
    """Delete checkpoint file after successful completion"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            os.remove(CHECKPOINT_FILE)
            print("Checkpoint file deleted (processing complete)")
        except Exception as e:
            print(f"Warning: Could not delete checkpoint file: {e}")
    
    # Also clean up partial results file if it exists
    if INCREMENTAL_SAVE and os.path.exists(PARTIAL_RESULTS_FILE):
        try:
            os.remove(PARTIAL_RESULTS_FILE)
            print("Partial results file deleted (will be replaced by final output)")
        except Exception as e:
            print(f"Warning: Could not delete partial results file: {e}")

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

def classify_edges_batch(edges_batch, api_key, endpoint_id, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
    """Classify a batch of edges using RunPod API with retry logic"""
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
    
    # Retry logic
    for attempt in range(max_retries):
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
            
            # If we get here, something went wrong but not a complete failure
            print(f"    API returned status {response.status_code}: {response.text[:200]}")
            
        except requests.exceptions.RequestException as e:
            print(f"    Request error on attempt {attempt + 1}/{max_retries}: {e}")
        except Exception as e:
            print(f"    Unexpected error on attempt {attempt + 1}/{max_retries}: {e}")
        
        # If this wasn't the last attempt, wait before retrying
        if attempt < max_retries - 1:
            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
            print(f"    Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
    
    # If all retries failed
    print(f"    ERROR: All {max_retries} attempts failed for this batch!")
    return None

def classify_all_edges(edges, api_key, endpoint_id, batch_size=50, checkpoint=None):
    """Classify all edges in batches with checkpoint/resume support"""
    classified_edges = []
    total_edges = len(edges)
    
    # Load previously classified edges from checkpoint if available
    start_batch = 0
    edges_processed_count = 0
    
    if checkpoint:
        start_batch = checkpoint.get('last_completed_batch', -1) + 1
        edges_processed_count = checkpoint.get('edges_processed_count', start_batch * batch_size)
        
        # If using incremental save, load from file instead of checkpoint
        if INCREMENTAL_SAVE:
            classified_edges = []  # Don't keep in memory
            print(f"Using incremental save mode - edges stored in {PARTIAL_RESULTS_FILE}")
        else:
            classified_edges = checkpoint.get('classified_edges', [])
        
        print(f"Resuming from batch {start_batch + 1}")
        print(f"Already processed {edges_processed_count} edges")
    
    print(f"\nClassifying {total_edges - edges_processed_count} remaining edges...")
    print(f"Checkpoint frequency: every {CHECKPOINT_FREQUENCY} batches")
    print("=" * 50)
    
    for batch_idx, i in enumerate(range(start_batch * batch_size, total_edges, batch_size), start=start_batch):
        batch = edges[i:i + batch_size]
        batch_num = batch_idx + 1
        total_batches = (total_edges + batch_size - 1) // batch_size
        
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} edges)...")
        
        # Try to classify with retries
        classifications = classify_edges_batch(batch, api_key, endpoint_id)
        
        if classifications is None:
            # All retries failed - ask user what to do
            print("\n" + "!" * 50)
            print("CRITICAL: Batch classification failed after all retries!")
            print("Options:")
            print("  1. Retry this batch (r)")
            print("  2. Skip this batch (s)")
            print("  3. Abort processing (a)")
            
            while True:
                choice = input("Your choice (r/s/a): ").lower().strip()
                if choice == 'r':
                    print("Retrying batch...")
                    classifications = classify_edges_batch(batch, api_key, endpoint_id)
                    if classifications:
                        break
                    else:
                        print("Retry failed again. Please choose another option.")
                elif choice == 's':
                    print("Skipping batch (marking as neutral)...")
                    classifications = [{'classification': 'neutral', 'confidence': 0.0, 'scores': {}} 
                                    for _ in batch]
                    break
                elif choice == 'a':
                    print("Aborting processing. Progress has been saved to checkpoint.")
                    # Save checkpoint before exiting
                    checkpoint_data = {
                        'classified_edges': classified_edges if not INCREMENTAL_SAVE else [],
                        'last_completed_batch': batch_idx - 1,
                        'total_edges': total_edges,
                        'edge_mode': EDGE_MODE,
                        'window_size': WINDOW_SIZE if EDGE_MODE == 'window' else None,
                        'edges_processed_count': edges_processed_count
                    }
                    save_checkpoint(checkpoint_data, force=True)
                    return None
                else:
                    print("Invalid choice. Please enter r, s, or a.")
            print("!" * 50 + "\n")
        
        # Process successful classifications
        batch_results = []
        for (source, target), classification in zip(batch, classifications):
            edge_result = {
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
            }
            batch_results.append(edge_result)
            edges_processed_count += 1
        
        # Save results incrementally or to memory
        if INCREMENTAL_SAVE:
            save_incremental_results(batch_results)
        else:
            classified_edges.extend(batch_results)
        
        processed = min(i + batch_size, total_edges)
        percent = (processed / total_edges) * 100
        print(f"  Progress: {processed}/{total_edges} edges ({percent:.1f}%)")
        
        # Save checkpoint at intervals
        checkpoint_data = {
            'classified_edges': classified_edges if not INCREMENTAL_SAVE else [],
            'last_completed_batch': batch_idx,
            'total_edges': total_edges,
            'edge_mode': EDGE_MODE,
            'window_size': WINDOW_SIZE if EDGE_MODE == 'window' else None,
            'edges_processed_count': edges_processed_count
        }
        save_checkpoint(checkpoint_data)
        
        if i + batch_size < total_edges:
            time.sleep(0.5)
    
    print("=" * 50)
    
    # If using incremental save, load all results for return
    if INCREMENTAL_SAVE:
        classified_edges = load_incremental_results()
    
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
    print("Edge Classification Pipeline with Optimized Resume Support")
    print("=" * 50)
    
    if API_KEY == "your-runpod-api-key-here":
        print("ERROR: Please update the API_KEY in this script with your RunPod API key")
        print("Get your API key from: https://runpod.io/console/user/settings")
        return
    
    try:
        # Check for existing checkpoint
        checkpoint = load_checkpoint()
        
        # If we have a checkpoint, check if it matches current configuration
        if checkpoint:
            if (checkpoint.get('edge_mode') != EDGE_MODE or 
                (EDGE_MODE == 'window' and checkpoint.get('window_size') != WINDOW_SIZE)):
                print("\nWARNING: Checkpoint configuration doesn't match current settings!")
                print(f"  Checkpoint: mode={checkpoint.get('edge_mode')}, window={checkpoint.get('window_size')}")
                print(f"  Current:    mode={EDGE_MODE}, window={WINDOW_SIZE if EDGE_MODE == 'window' else None}")
                
                choice = input("\nDo you want to (c)ontinue with checkpoint or (s)tart fresh? (c/s): ").lower()
                if choice == 's':
                    checkpoint = None
                    delete_checkpoint()
        
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
        
        # If resuming, skip edge generation message
        if checkpoint and checkpoint.get('last_completed_batch', -1) >= 0:
            print("\nResuming from checkpoint - regenerating edges for continuation")
            # We need to regenerate edges to continue processing
            if EDGE_MODE == "all":
                edges = generate_edges(literals, section_order, mode="all")
            elif EDGE_MODE == "same":
                edges = generate_edges(literals, section_order, mode="same")
            elif EDGE_MODE == "window":
                edges = generate_edges(literals, section_order, mode="window", window_size=WINDOW_SIZE)
        else:
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
        classified_edges = classify_all_edges(edges, API_KEY, ENDPOINT_ID, BATCH_SIZE, checkpoint)
        
        if classified_edges is None:
            print("\nProcessing aborted by user. You can resume later by running the script again.")
            return
        
        elapsed = time.time() - start_time
        
        print(f"\nClassification completed in {elapsed:.1f} seconds")
        print(f"Average time per edge: {elapsed/len(edges)*1000:.1f}ms")
        
        # Save results
        save_results(classified_edges, literals, OUTPUT_FILE, EDGE_MODE, 
                    WINDOW_SIZE if EDGE_MODE == "window" else None)
        
        # Delete checkpoint file since we're done
        delete_checkpoint()
        
        print("\n✅ Pipeline completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
        print("Progress has been saved. You can resume by running the script again.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nProgress has been saved. You can resume by running the script again.")

if __name__ == "__main__":
    main()