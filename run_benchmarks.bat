@echo off
setlocal

echo RPC Benchmark Suite
echo ==================

:: Simply pass all arguments directly to the Python script
python run_benchmarks.py %*
if %errorlevel% neq 0 (
    echo Error running benchmarks. Exiting.
    exit /b %errorlevel%
)

echo.
echo Benchmarks completed. Generating report...
python generate_report.py --results-dir benchmark_results\latest
if %errorlevel% neq 0 (
    echo Error generating report. Exiting.
    exit /b %errorlevel%
)

echo.
echo View results with:
echo   python view_results.py --results-dir benchmark_results\latest
echo   python view_results.py --results-dir benchmark_results\latest --implementation rpyc
echo   python view_results.py --results-dir benchmark_results\latest --test test_benchmark_simple_call

echo.
echo Generating dashboard...
python benchmark_dashboard.py --results-dir benchmark_results\latest
if %errorlevel% neq 0 (
    echo Error generating dashboard. Exiting.
    exit /b %errorlevel%
)

endlocal
