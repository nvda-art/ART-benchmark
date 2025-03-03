@echo off
setlocal

echo RPC Benchmark Suite
echo ==================

:: Simply pass all arguments directly to the Python script
python run_benchmarks.py %*

echo.
echo Benchmarks completed. Generating report...
python generate_report.py --results-dir benchmark_results\latest

echo.
echo View results with:
echo   python view_results.py --results-dir benchmark_results\latest
echo   python view_results.py --results-dir benchmark_results\latest --implementation rpyc
echo   python view_results.py --results-dir benchmark_results\latest --test test_benchmark_simple_call

echo.
echo Generating dashboard...
python benchmark_dashboard.py --results-dir benchmark_results\latest

endlocal
