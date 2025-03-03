#!/usr/bin/env python
import argparse
import subprocess
import json
import os
import sys
import time
import signal
from datetime import datetime

def main():
    # Configure logging
    import logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s %(levelname)s: %(message)s',
                        stream=sys.stdout)
    logging.info("Starting benchmark run")
    parser = argparse.ArgumentParser(description="Run RPC benchmarks and collect results")
    parser.add_argument("--implementations", nargs="+", 
                        choices=["rpyc", "zmq", "grpc", "named-pipe"],
                        default=["rpyc", "zmq", "grpc"],
                        help="RPC implementations to benchmark")
    parser.add_argument("--isolated", action="store_true", 
                        help="Run servers in isolated processes")
    parser.add_argument("--test", type=str, help="Specific test pattern to run")
    parser.add_argument("--output-dir", type=str, default="benchmark_results",
                        help="Directory to store results")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Timeout in seconds for each implementation's benchmark")
    args = parser.parse_args()
    
    # Create results directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = os.path.join(args.output_dir, timestamp)
    os.makedirs(results_dir, exist_ok=True)
    
    # Create a symlink to the latest results
    latest_link = os.path.join(args.output_dir, "latest")
    if os.path.exists(latest_link) and os.path.islink(latest_link):
        os.unlink(latest_link)
    elif os.path.exists(latest_link):
        os.remove(latest_link)
    
    if sys.platform.startswith("win"):
        # Windows doesn't support symlinks easily, so we'll create a text file with the path
        with open(latest_link, "w") as f:
            # Use normalized path with forward slashes for consistency
            f.write(results_dir.replace('\\', '/'))
    else:
        os.symlink(results_dir, latest_link, target_is_directory=True)
    
    # Run benchmarks for each implementation
    for impl in args.implementations:
        if impl == "named-pipe" and not sys.platform.startswith("win"):
            print("Skipping named-pipe benchmarks on non-Windows platform")
            continue
            
        result_file = os.path.join(results_dir, f"{impl}_results.json")
        cmd = ["pytest", "-v", "--benchmark-enable", "--benchmark-json", result_file]
        
        if args.isolated:
            cmd.append("--rpc-isolated")
        
        cmd.extend([f"--rpc={impl}"])
        
        if args.test:
            cmd.append(args.test)
        
        # Always add timeout but make sure it's properly formatted for pytest-timeout
        cmd.extend([f"--timeout={args.timeout}"])
        
        print(f"\n=== Running benchmarks for {impl} (isolated={args.isolated}) ===")
        print(f"Command: {' '.join(cmd)}")
        
        # Run with timeout to prevent hanging
        try:
            # Use universal_newlines=True for better text handling
            print(f"Executing: {' '.join(cmd)}")
            
            # Set a timeout per implementation
            timeout = args.timeout  # seconds
            
            # Run the process with a timeout
            try:
                # Use check=True to raise an exception if the process fails
                process = subprocess.run(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    text=True, 
                    timeout=timeout,
                    check=False  # Don't raise on non-zero exit
                )
                
                # Print the output
                print(process.stdout)
                
                if process.returncode != 0:
                    print(f"Warning: Benchmark for {impl} exited with code {process.returncode}")
                    
            except subprocess.TimeoutExpired as e:
                print(f"\nTimeout reached for {impl} after {timeout} seconds.")
                print(f"Partial output: {e.stdout}")
                print(f"Benchmark for {impl} was terminated due to timeout.")
                
        except Exception as e:
            print(f"Error running benchmark for {impl}: {e}")
            # Make sure we clean up any running processes
            if 'process' in locals() and process.poll() is None:
                process.kill()
    
    # Check for successful benchmarks
    successful_implementations = []
    for impl in args.implementations:
        result_file = os.path.join(results_dir, f"{impl}_results.json")
        if os.path.exists(result_file) and os.path.getsize(result_file) > 0:
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    if 'benchmarks' in data and data['benchmarks']:
                        successful_implementations.append(impl)
            except:
                print(f"Warning: Invalid results for {impl}")
        else:
            print(f"Warning: No valid results for {impl}")

    print(f"All benchmarks completed. Results saved to {results_dir}")
    print(f"Successful implementations: {', '.join(successful_implementations) if successful_implementations else 'None'}")
    
    if not successful_implementations:
        print("Warning: No successful benchmarks. Report generation may fail.")
    
    print("Generating report...")
    try:
        # Run report generation with a timeout
        result = subprocess.run([sys.executable, "generate_report.py", "--results-dir", results_dir], 
                      timeout=60, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            print(f"Report generated successfully in {results_dir}")
        else:
            print(f"Error generating report: {result.stderr}")
            print("Check the results directory manually.")
    except subprocess.TimeoutExpired:
        print("Report generation timed out. Check the results directory manually.")
    except Exception as e:
        print(f"Error running report generation: {e}")
        print("Check the results directory manually.")

if __name__ == "__main__":
    main()
