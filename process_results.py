#!/usr/bin/env python
import json
import os
import pandas as pd
from collections import defaultdict

def load_benchmark_data(results_dir):
    """Load benchmark data from JSON files and convert to structured format."""
    data = []
    
    # Check if directory exists
    if not os.path.exists(results_dir):
        print(f"Error: Results directory {results_dir} does not exist")
        return pd.DataFrame()
    
    # Get list of result files
    result_files = [f for f in os.listdir(results_dir) if f.endswith("_results.json")]
    if not result_files:
        print(f"Warning: No benchmark result files found in {results_dir}")
        return pd.DataFrame()
    
    for filename in result_files:
        if not filename.endswith("_results.json"):
            continue
            
        impl_name = filename.split("_")[0]
        filepath = os.path.join(results_dir, filename)
        
        try:
            # Check if file is empty or invalid
            if os.path.getsize(filepath) == 0:
                print(f"Warning: Empty benchmark file {filepath}")
                continue
                
            with open(filepath, 'r') as f:
                try:
                    benchmark_data = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"Error processing {filepath}: {e}")
                    continue
                
            if 'benchmarks' not in benchmark_data or not benchmark_data['benchmarks']:
                print(f"Warning: No benchmarks found in {filepath}")
                continue
                
            for benchmark in benchmark_data['benchmarks']:
                test_name = benchmark['name'].split('[')[0]
                stats = {
                    'implementation': impl_name,
                    'test': test_name,
                    'mean': benchmark['stats']['mean'],
                    'min': benchmark['stats']['min'],
                    'max': benchmark['stats']['max'],
                    'median': benchmark['stats']['median'],
                    'stddev': benchmark['stats']['stddev'],
                    'ops': 1.0 / benchmark['stats']['mean'],  # operations per second
                    'rounds': benchmark['stats']['rounds'],
                }
                data.append(stats)
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
    
    if not data:
        print("Warning: No valid benchmark data found in any files")
        return pd.DataFrame()
        
    return pd.DataFrame(data)

def calculate_comparisons(df):
    """Calculate relative performance between implementations."""
    comparisons = defaultdict(dict)
    
    # Check if dataframe is empty
    if df.empty:
        return comparisons
    
    for test in df['test'].unique():
        test_df = df[df['test'] == test]
        
        # Skip tests with only one implementation
        if len(test_df) < 2:
            baseline = test_df['mean'].iloc[0]
            fastest_impl = test_df['implementation'].iloc[0]
        else:
            baseline = test_df['mean'].min()  # Use fastest implementation as baseline
            fastest_impl = test_df.loc[test_df['mean'].idxmin()]['implementation']
        
        for _, row in test_df.iterrows():
            impl = row['implementation']
            relative = row['mean'] / baseline
            comparisons[test][impl] = {
                'mean_time': row['mean'],
                'relative': relative,
                'ops_per_sec': row['ops'],
                'is_fastest': impl == fastest_impl
            }
    
    return comparisons

def process_results(results_dir):
    """Process benchmark results and return structured data for reporting."""
    df = load_benchmark_data(results_dir)
    
    # Handle empty dataframe case
    if df.empty:
        empty_summary = {
            'fastest_by_test': {},
            'test_count': 0,
            'total_rounds': 0,
            'implementations': [],
            'win_counts': {}
        }
        return {
            'raw_data': df,
            'comparisons': {},
            'summary': empty_summary
        }
    
    comparisons = calculate_comparisons(df)
    
    # Calculate summary statistics
    summary = {
        'fastest_by_test': {},
        'test_count': len(df['test'].unique()),
        'total_rounds': df['rounds'].sum() if 'rounds' in df.columns else 0,
        'implementations': sorted(df['implementation'].unique().tolist()),
    }
    
    # Find fastest implementation for each test
    for test in df['test'].unique():
        test_df = df[df['test'] == test]
        if not test_df.empty:
            fastest_idx = test_df['mean'].idxmin()
            if fastest_idx is not None:
                fastest = test_df.loc[fastest_idx]
                summary['fastest_by_test'][test] = {
                    'implementation': fastest['implementation'],
                    'mean_time': fastest['mean'],
                    'ops_per_sec': fastest['ops']
                }
    
    # Count wins by implementation
    win_counts = {}
    for test, fastest in summary['fastest_by_test'].items():
        impl = fastest['implementation']
        win_counts[impl] = win_counts.get(impl, 0) + 1
    
    summary['win_counts'] = win_counts
    
    return {
        'raw_data': df,
        'comparisons': comparisons,
        'summary': summary
    }

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Process benchmark results")
    parser.add_argument("--results-dir", required=True, help="Directory containing benchmark results")
    parser.add_argument("--output", default="processed_results.json", help="Output file for processed results")
    args = parser.parse_args()
    
    # Handle the "latest" symlink on Windows
    results_dir = os.path.normpath(args.results_dir)
    if os.path.basename(results_dir) == "latest" and os.path.isfile(results_dir):
        # On Windows, this might be a text file with the path
        try:
            with open(results_dir, 'r') as f:
                results_dir = f.read().strip()
                print(f"Resolved 'latest' to: {results_dir}")
        except Exception as e:
            print(f"Error resolving 'latest' symlink: {e}")
    
    if not os.path.exists(results_dir):
        print(f"Error: Results directory {results_dir} does not exist")
        sys.exit(1)
    
    results = process_results(results_dir)
    
    if results['raw_data'].empty:
        print("No valid benchmark data found. Cannot generate reports.")
        sys.exit(1)
    
    # Save raw data as CSV
    csv_path = os.path.join(results_dir, "benchmark_data.csv")
    try:
        results['raw_data'].to_csv(csv_path, index=False)
        print(f"Raw data saved to {csv_path}")
    except Exception as e:
        print(f"Error saving CSV data: {e}")
    
    # Save comparisons and summary as JSON
    output = {
        'comparisons': results['comparisons'],
        'summary': results['summary']
    }
    
    # Custom JSON encoder to handle NumPy types
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            import numpy as np
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return super(NumpyEncoder, self).default(obj)
    
    output_path = os.path.join(results_dir, args.output)
    try:
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2, cls=NumpyEncoder)
        print(f"Processed results saved to {output_path}")
    except Exception as e:
        print(f"Error saving processed results: {e}")
        sys.exit(1)
