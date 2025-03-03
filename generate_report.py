#!/usr/bin/env python
import argparse
import json
import os
import sys
import pandas as pd
from tabulate import tabulate
from datetime import datetime

def format_time(seconds):
    """Format time in a human-readable way based on magnitude."""
    if seconds < 0.000001:  # less than 1 microsecond
        return f"{seconds * 1e9:.2f} ns"
    elif seconds < 0.001:  # less than 1 millisecond
        return f"{seconds * 1e6:.2f} µs"
    elif seconds < 1:  # less than 1 second
        return f"{seconds * 1e3:.2f} ms"
    else:
        return f"{seconds:.4f} s"

def generate_summary_report(results, output_file):
    """Generate a summary report in plain text format."""
    with open(output_file, 'w') as f:
        f.write("RPC BENCHMARK SUMMARY REPORT\n")
        f.write("===========================\n\n")
        
        # Write timestamp
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Write summary statistics
        summary = results['summary']
        f.write("OVERVIEW\n")
        f.write("--------\n")
        f.write(f"Total tests: {summary['test_count']}\n")
        f.write(f"Total benchmark rounds: {summary['total_rounds']}\n")
        f.write(f"Implementations tested: {', '.join(summary['implementations'])}\n\n")
        
        # Write win counts
        f.write("PERFORMANCE WINS BY IMPLEMENTATION\n")
        f.write("----------------------------------\n")
        for impl, count in summary['win_counts'].items():
            f.write(f"{impl}: {count} test(s)\n")
        f.write("\n")
        
        # Write fastest implementation for each test
        f.write("FASTEST IMPLEMENTATION BY TEST\n")
        f.write("-----------------------------\n")
        for test, data in summary['fastest_by_test'].items():
            f.write(f"Test: {test}\n")
            f.write(f"  Fastest: {data['implementation']}\n")
            f.write(f"  Mean time: {format_time(data['mean_time'])}\n")
            f.write(f"  Operations per second: {data['ops_per_sec']:.2f}\n\n")
        
        # Write detailed comparison tables for each test
        f.write("DETAILED TEST COMPARISONS\n")
        f.write("------------------------\n\n")
        
        for test, impls in results['comparisons'].items():
            f.write(f"Test: {test}\n")
            f.write(f"{'-' * (len(test) + 6)}\n\n")
            
            # Create a table for this test
            table_data = []
            headers = ["Implementation", "Mean Time", "Relative Speed", "Ops/Second"]
            
            for impl, data in impls.items():
                marker = " (fastest)" if data['is_fastest'] else ""
                row = [
                    f"{impl}{marker}",
                    format_time(data['mean_time']),
                    f"{data['relative']:.2f}x",
                    f"{data['ops_per_sec']:.2f}"
                ]
                table_data.append(row)
            
            # Sort by mean time (fastest first)
            table_data.sort(key=lambda x: float(x[1].split()[0]))
            
            # Write the table
            f.write(tabulate(table_data, headers=headers, tablefmt="grid"))
            f.write("\n\n")
        
        # Write explanation of metrics
        f.write("EXPLANATION OF METRICS\n")
        f.write("---------------------\n")
        f.write("Mean Time: Average execution time per operation\n")
        f.write("Relative Speed: How many times slower than the fastest implementation (1.00x is fastest)\n")
        f.write("Ops/Second: Operations per second (higher is better)\n")

def generate_csv_report(results, output_file):
    """Generate a CSV report for easy import into spreadsheets."""
    # Create a flattened dataframe for the CSV
    rows = []
    
    for test, impls in results['comparisons'].items():
        for impl, data in impls.items():
            row = {
                'Test': test,
                'Implementation': impl,
                'Mean Time (s)': data['mean_time'],
                'Relative Speed': data['relative'],
                'Operations/Second': data['ops_per_sec'],
                'Is Fastest': data['is_fastest']
            }
            rows.append(row)
    
    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)

def main():
    parser = argparse.ArgumentParser(description="Generate accessible benchmark reports")
    parser.add_argument("--results-dir", required=True, help="Directory containing processed results")
    args = parser.parse_args()
    
    # Load processed results
    # Normalize path to handle Windows/Unix path differences
    results_dir = os.path.normpath(args.results_dir)
    
    # Handle the "latest" symlink on Windows
    if os.path.basename(results_dir) == "latest" and os.path.isfile(results_dir):
        # On Windows, this might be a text file with the path
        with open(results_dir, 'r') as f:
            resolved_dir = f.read().strip()
            print(f"Resolved 'latest' to: {resolved_dir}")
            results_dir = resolved_dir  # Use the resolved path for all subsequent operations
    
    # Ensure the directory exists
    os.makedirs(results_dir, exist_ok=True)
    
    # Now use the resolved path for all file operations
    results_file = os.path.join(results_dir, "processed_results.json")
    
    if not os.path.exists(results_file):
        # If processed results don't exist, run the processing script
        import subprocess
        print(f"Processed results not found at {results_file}, generating them now...")
        try:
            # Use the full path to process_results.py to avoid path issues
            script_dir = os.path.dirname(os.path.abspath(__file__))
            process_script = os.path.join(script_dir, "process_results.py")
            subprocess.run([sys.executable, process_script, "--results-dir", results_dir], 
                          check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Error processing results: {e}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            sys.exit(1)
    
    # Check again if the file exists after processing
    if not os.path.exists(results_file):
        print(f"Error: Results file still not found at {results_file} after processing")
        sys.exit(1)
        
    try:
        with open(results_file, 'r') as f:
            results = json.load(f)
    except Exception as e:
        print(f"Error loading results file {results_file}: {e}")
        sys.exit(1)
    
    # Generate reports - use the resolved results_dir path
    txt_report = os.path.join(results_dir, "benchmark_report.txt")
    csv_report = os.path.join(results_dir, "benchmark_report.csv")
    
    # Ensure the directory exists before writing files
    os.makedirs(os.path.dirname(txt_report), exist_ok=True)
    
    generate_summary_report(results, txt_report)
    generate_csv_report(results, csv_report)
    
    print(f"Text report generated: {txt_report}")
    print(f"CSV report generated: {csv_report}")
    
    # Print a brief summary to the console
    summary = results['summary']
    print("\nBRIEF SUMMARY:")
    print("-------------")
    print(f"Total tests: {summary['test_count']}")
    print("Fastest implementation by test count:")
    for impl, count in summary['win_counts'].items():
        print(f"  {impl}: {count} test(s)")

if __name__ == "__main__":
    main()
