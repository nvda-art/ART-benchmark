#!/usr/bin/env python
import argparse
import json
import os
import subprocess
import sys
import time
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
    parser.add_argument("--timeout", type=int, default=30,
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
        cmd = [
            "pytest",
            "-v", "-xvs", # Keep existing verbose flags
            "--benchmark-enable",
            "--benchmark-json", result_file,
            "--log-cli-level=DEBUG", # Enable DEBUG level logging for tests
            "--tb=short" # Shorten pytest tracebacks on failure
        ]
        
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
                
            # Run with timeout using subprocess.run for better handling
            try:
                result = subprocess.run(
                    cmd,
                    timeout=args.timeout,
                    capture_output=True,  # Capture stdout/stderr
                    text=True,            # Decode as text
                    check=False           # Don't raise exception on non-zero exit, check manually
                )

                # Print captured output
                if result.stdout:
                    print("--- Benchmark Output ---")
                    print(result.stdout)
                    print("------------------------")
                if result.stderr:
                    print("--- Benchmark Errors ---")
                    print(result.stderr)
                    print("------------------------")

                if result.returncode != 0:
                    print(f"Error: Benchmark for {impl} exited with code {result.returncode}")
                    print("Stopping all benchmarks due to failure.")
                    sys.exit(1) # Fail early on non-zero return code

            except subprocess.TimeoutExpired as e:
                print(f"\nTimeout reached for {impl} after {args.timeout} seconds.")
                print(f"Benchmark for {impl} was terminated due to timeout.")
                # Print any captured output before timeout
                if e.stdout:
                    print("--- Output before timeout ---")
                    print(e.stdout)
                    print("-----------------------------")
                if e.stderr:
                    print("--- Errors before timeout ---")
                    print(e.stderr)
                    print("-----------------------------")
                sys.exit(1) # Fail early on timeout

            except Exception as e:
                print(f"\nError during benchmark execution for {impl}: {e}")
                print("Stopping all benchmarks due to failure.")
                sys.exit(1) # Fail early on other exceptions
                
        except Exception as e:
            print(f"Error running benchmark for {impl}: {e}")
            print("Stopping all benchmarks due to failure.")
            # Make sure we clean up any running processes
            if 'process' in locals():
                try:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=5)  # Wait for process to terminate
                except Exception as e:
                    print(f"Error killing process: {e}")
            sys.exit(1)  # Fail early on exception
    
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
                print(f"Error: Invalid results for {impl}")
                sys.exit(1)  # Fail early on invalid results
        else:
            print(f"Error: No valid results for {impl}")
            sys.exit(1)  # Fail early on missing results

    print(f"All benchmarks completed. Results saved to {results_dir}")
    print(f"Successful implementations: {', '.join(successful_implementations)}")
    
    if not successful_implementations:
        print("Error: No successful benchmarks. Report generation will fail.")
        sys.exit(1)  # Fail early if no successful implementations
    
    print("Generating report...")
    try:
        # Run report generation with a timeout
        result = subprocess.run([sys.executable, "generate_report.py", "--results-dir", results_dir], 
                      timeout=60, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            print(f"Report generated successfully in {results_dir}")
        else:
            print(f"Error generating report: {result.stderr}")
            sys.exit(1)  # Fail early on report generation error
    except subprocess.TimeoutExpired:
        print("Error: Report generation timed out.")
        sys.exit(1)  # Fail early on timeout
    except Exception as e:
        print(f"Error running report generation: {e}")
        sys.exit(1)  # Fail early on exception

if __name__ == "__main__":
    main()
