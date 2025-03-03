# RPC Benchmark Suite PowerShell Script

param (
    [string[]]$Implementations = @(),
    [switch]$Isolated,
    [string]$Test = "",
    [string]$OutputDir = "benchmark_results",
    [switch]$Help
)

# Show help if requested
if ($Help) {
    Write-Host "Usage: .\run_benchmarks.ps1 [-Implementations impl1,impl2,...] [-Isolated] [-Test testname] [-OutputDir dir]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Implementations   RPC implementations to benchmark (rpyc, zmq, grpc, named-pipe)"
    Write-Host "  -Isolated          Run servers in isolated processes"
    Write-Host "  -Test              Specific test pattern to run"
    Write-Host "  -OutputDir         Directory to store results (default: benchmark_results)"
    Write-Host "  -Help              Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\run_benchmarks.ps1 -Implementations rpyc,zmq"
    Write-Host "  .\run_benchmarks.ps1 -Isolated -Test test_benchmark_simple_call"
    exit
}

# Set default implementations if none provided
if ($Implementations.Count -eq 0) {
    if ($env:OS -eq "Windows_NT") {
        $Implementations = @("rpyc", "zmq", "grpc", "named-pipe")
    } else {
        $Implementations = @("rpyc", "zmq", "grpc")
    }
}

# Build command arguments
$IsolatedArg = if ($Isolated) { "--rpc-isolated" } else { "" }
$TestArg = if ($Test) { "--test $Test" } else { "" }

Write-Host "RPC Benchmark Suite"
Write-Host "=================="
Write-Host ""
Write-Host "Running benchmarks with the following configuration:"
Write-Host "  Implementations: $($Implementations -join ', ')"
Write-Host "  Isolated: $Isolated"
Write-Host "  Test: $Test"
Write-Host "  Output directory: $OutputDir"
Write-Host ""

# Run the benchmarks
$ImplArgs = $Implementations -join " "
$Command = "python run_benchmarks.py --implementations $ImplArgs $IsolatedArg $TestArg --output-dir $OutputDir"
Write-Host "Executing: $Command"
Invoke-Expression $Command

Write-Host ""
Write-Host "Benchmarks completed. Generating report..."
python generate_report.py --results-dir "$OutputDir\latest"

Write-Host ""
Write-Host "View results with:"
Write-Host "  python view_results.py --results-dir $OutputDir\latest"
Write-Host "  python view_results.py --results-dir $OutputDir\latest --implementation rpyc"
Write-Host "  python view_results.py --results-dir $OutputDir\latest --test test_benchmark_simple_call"

Write-Host ""
Write-Host "Generating dashboard..."
python benchmark_dashboard.py --results-dir "$OutputDir\latest"
