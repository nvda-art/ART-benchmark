#!/usr/bin/env python
import argparse
import json
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from tabulate import tabulate

def load_results(results_dir):
    """Load processed benchmark results."""
    # Ensure the directory exists
    os.makedirs(results_dir, exist_ok=True)
    
    results_file = os.path.join(results_dir, "processed_results.json")
    if not os.path.exists(results_file):
        print(f"Results file not found: {results_file}")
        print("Run generate_report.py first to process the benchmark results.")
        sys.exit(1)
    
    with open(results_file, 'r') as f:
        return json.load(f)

def plot_comparison_chart(results, output_dir):
    """Generate a bar chart comparing implementations across tests."""
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    comparisons = results['comparisons']
    
    # Prepare data for plotting
    tests = list(comparisons.keys())
    implementations = results['summary']['implementations']
    
    # Create a figure with subplots for each test
    fig, axes = plt.subplots(len(tests), 1, figsize=(10, 5 * len(tests)))
    if len(tests) == 1:
        axes = [axes]
    
    for i, test in enumerate(tests):
        ax = axes[i]
        test_data = comparisons[test]
        
        # Extract data for this test
        impl_names = []
        mean_times = []
        colors = []
        
        for impl in implementations:
            if impl in test_data:
                impl_names.append(impl)
                mean_times.append(test_data[impl]['mean_time'] * 1000)  # Convert to ms
                colors.append('green' if test_data[impl]['is_fastest'] else 'blue')
        
        # Sort by mean time
        sorted_indices = np.argsort(mean_times)
        impl_names = [impl_names[j] for j in sorted_indices]
        mean_times = [mean_times[j] for j in sorted_indices]
        colors = [colors[j] for j in sorted_indices]
        
        # Plot
        bars = ax.bar(impl_names, mean_times, color=colors)
        ax.set_title(f"Test: {test}")
        ax.set_ylabel("Mean Time (ms)")
        ax.set_xlabel("Implementation")
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}ms',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')
    
    plt.tight_layout()
    chart_path = os.path.join(output_dir, "comparison_chart.png")
    plt.savefig(chart_path)
    print(f"Comparison chart saved to: {chart_path}")
    return chart_path

def plot_win_chart(results, output_dir):
    """Generate a pie chart showing win distribution."""
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    win_counts = results['summary']['win_counts']
    
    # Prepare data for plotting
    labels = list(win_counts.keys())
    sizes = list(win_counts.values())
    
    # Create pie chart
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    ax.set_title("Performance Wins by Implementation")
    
    # Save chart
    chart_path = os.path.join(output_dir, "win_distribution.png")
    plt.savefig(chart_path)
    print(f"Win distribution chart saved to: {chart_path}")
    return chart_path

def generate_html_report(results, output_dir, comparison_chart, win_chart):
    """Generate an HTML report with interactive elements."""
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>RPC Benchmark Results</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #333; }}
            .chart {{ margin: 20px 0; text-align: center; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .fastest {{ background-color: #d4edda; }}
            .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <h1>RPC Benchmark Results</h1>
        
        <div class="summary">
            <h2>Summary</h2>
            <p>Total tests: {results['summary']['test_count']}</p>
            <p>Implementations tested: {', '.join(results['summary']['implementations'])}</p>
        </div>
        
        <div class="chart">
            <h2>Performance Comparison</h2>
            <img src="{os.path.basename(comparison_chart)}" alt="Performance Comparison Chart" width="800">
        </div>
        
        <div class="chart">
            <h2>Win Distribution</h2>
            <img src="{os.path.basename(win_chart)}" alt="Win Distribution Chart" width="500">
        </div>
        
        <h2>Detailed Results</h2>
    """
    
    # Add tables for each test
    for test, impls in results['comparisons'].items():
        html_content += f"""
        <h3>Test: {test}</h3>
        <table>
            <tr>
                <th>Implementation</th>
                <th>Mean Time</th>
                <th>Relative Speed</th>
                <th>Operations/Second</th>
            </tr>
        """
        
        # Sort implementations by mean time
        sorted_impls = sorted(impls.items(), key=lambda x: x[1]['mean_time'])
        
        for impl, data in sorted_impls:
            fastest_class = " class='fastest'" if data['is_fastest'] else ""
            mean_time = format_time(data['mean_time'])
            relative = f"{data['relative']:.2f}x"
            ops_per_sec = f"{data['ops_per_sec']:.2f}"
            
            html_content += f"""
            <tr{fastest_class}>
                <td>{impl}</td>
                <td>{mean_time}</td>
                <td>{relative}</td>
                <td>{ops_per_sec}</td>
            </tr>
            """
        
        html_content += "</table>"
    
    html_content += """
    </body>
    </html>
    """
    
    html_path = os.path.join(output_dir, "benchmark_report.html")
    with open(html_path, 'w') as f:
        f.write(html_content)
    
    print(f"HTML report generated: {html_path}")
    return html_path

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

def main():
    parser = argparse.ArgumentParser(description="Generate visual dashboard for benchmark results")
    parser.add_argument("--results-dir", default="benchmark_results/latest", 
                        help="Directory containing processed results")
    args = parser.parse_args()
    
    try:
        # Check if matplotlib is installed
        import matplotlib
    except ImportError:
        print("matplotlib is required for dashboard generation.")
        print("Install it with: pip install matplotlib")
        sys.exit(1)
    
    # Normalize the results directory path
    results_dir = os.path.normpath(args.results_dir)
    
    # Handle the "latest" symlink on Windows
    if os.path.basename(results_dir) == "latest" and os.path.isfile(results_dir):
        with open(results_dir, 'r') as f:
            results_dir = f.read().strip()
            print(f"Resolved 'latest' to: {results_dir}")
    
    # Ensure the directory exists
    os.makedirs(results_dir, exist_ok=True)
    
    try:
        results = load_results(results_dir)
        
        # Check if there's any data to plot
        if not results['summary']['implementations']:
            print("No valid benchmark data found. Skipping dashboard generation.")
            return
            
        # Generate charts using the resolved directory
        comparison_chart = plot_comparison_chart(results, results_dir)
        win_chart = plot_win_chart(results, results_dir)
        
        # Generate HTML report
        html_report = generate_html_report(results, results_dir, comparison_chart, win_chart)
        
        print("\nDashboard generation complete!")
        print(f"Open the HTML report to view the results: {html_report}")
        
        # Try to open the HTML report automatically
        if sys.platform.startswith('win'):
            os.system(f'start {html_report}')
        elif sys.platform.startswith('darwin'):  # macOS
            os.system(f'open {html_report}')
        else:  # Linux
            os.system(f'xdg-open {html_report}')
    except Exception as e:
        print(f"Error generating dashboard: {e}")
    
    print("\nDashboard generation complete!")
    print(f"Open the HTML report to view the results: {html_report}")
    
    # Try to open the HTML report automatically
    if sys.platform.startswith('win'):
        os.system(f'start {html_report}')
    elif sys.platform.startswith('darwin'):  # macOS
        os.system(f'open {html_report}')
    else:  # Linux
        os.system(f'xdg-open {html_report}')

if __name__ == "__main__":
    main()
