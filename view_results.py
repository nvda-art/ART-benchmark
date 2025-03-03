#!/usr/bin/env python
import argparse
import json
import os
import pandas as pd
from tabulate import tabulate

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

def view_summary(results):
    """Display a summary of benchmark results."""
    summary = results['summary']
    
    print("BENCHMARK SUMMARY")
    print("=================")
    print(f"Total tests: {summary['test_count']}")
    print(f"Implementations tested: {', '.join(summary['implementations'])}")
    print("\nPerformance wins by implementation:")
    
    for impl, count in summary['win_counts'].items():
        print(f"  {impl}: {count} test(s)")
    
    print("\nFastest implementation by test:")
    for test, data in summary['fastest_by_test'].items():
        print(f"  {test}: {data['implementation']} ({format_time(data['mean_time'])})")

def view_test_details(results, test_name=None):
    """Display detailed results for a specific test or all tests."""
    if test_name:
        if test_name not in results['comparisons']:
            print(f"Test '{test_name}' not found in results.")
            return
        tests = {test_name: results['comparisons'][test_name]}
    else:
        tests = results['comparisons']
    
    for test, impls in tests.items():
        print(f"\nTEST: {test}")
        print("=" * (len(test) + 6))
        
        # Create a table for this test
        table_data = []
        
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
        
        # Print the table
        headers = ["Implementation", "Mean Time", "Relative Speed", "Ops/Second"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

def view_implementation_details(results, impl_name):
    """Display detailed results for a specific implementation."""
    if impl_name not in results['summary']['implementations']:
        print(f"Implementation '{impl_name}' not found in results.")
        return
    
    print(f"\nRESULTS FOR: {impl_name}")
    print("=" * (len(impl_name) + 13))
    
    # Count wins
    win_count = results['summary']['win_counts'].get(impl_name, 0)
    print(f"Total wins: {win_count} out of {results['summary']['test_count']} tests")
    
    # Create a table of all test results for this implementation
    table_data = []
    
    for test, impls in results['comparisons'].items():
        if impl_name in impls:
            data = impls[impl_name]
            fastest_impl = next((i for i, d in impls.items() if d['is_fastest']), None)
            
            row = [
                test,
                format_time(data['mean_time']),
                f"{data['relative']:.2f}x",
                f"{data['ops_per_sec']:.2f}",
                "Yes" if data['is_fastest'] else f"No ({fastest_impl})"
            ]
            table_data.append(row)
    
    # Sort by test name
    table_data.sort(key=lambda x: x[0])
    
    # Print the table
    headers = ["Test", "Mean Time", "Relative Speed", "Ops/Second", "Is Fastest?"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def main():
    parser = argparse.ArgumentParser(description="View benchmark results")
    parser.add_argument("--results-dir", default="benchmark_results/latest", 
                        help="Directory containing processed results")
    parser.add_argument("--test", help="Show details for a specific test")
    parser.add_argument("--implementation", help="Show details for a specific implementation")
    args = parser.parse_args()
    
    # Handle the "latest" symlink on Windows
    results_dir = os.path.normpath(args.results_dir)
    if os.path.basename(results_dir) == "latest" and os.path.isfile(results_dir):
        # On Windows, this might be a text file with the path
        with open(results_dir, 'r') as f:
            results_dir = f.read().strip()
            print(f"Resolved 'latest' to: {results_dir}")
    
    # Load processed results
    results_file = os.path.join(results_dir, "processed_results.json")
    if not os.path.exists(results_file):
        print(f"Results file not found: {results_file}")
        return
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    # Display results based on arguments
    if args.implementation:
        view_implementation_details(results, args.implementation)
    elif args.test:
        view_test_details(results, args.test)
    else:
        view_summary(results)
        print("\nFor detailed test results, use --test or --implementation")

if __name__ == "__main__":
    main()
