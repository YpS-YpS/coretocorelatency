@echo off
setlocal enabledelayedexpansion

rem =========================================================================
rem  start.bat - one-click core-to-core latency benchmark + heatmap
rem
rem  Usage:
rem    start.bat                  baseline preset (5000 x 300) - DEFAULT
rem    start.bat quick            fast/noisy   (1000 x 100)
rem    start.bat baseline         notebook     (5000 x 300)
rem    start.bat publication      clean        (30000 x 1000)
rem    start.bat <iters> <samples>  custom counts
rem
rem  Environment variables (set before calling):
rem    ANNOT_MAX=N  override the core-count threshold for per-cell numbers.
rem                 Default 9999 (always show numbers, any core count).
rem                 Lower it (e.g. set ANNOT_MAX=24) to suppress numbers on
rem                 large matrices if the image gets too big for your viewer.
rem
rem  Approximate wall-clock runtime scales as ~n^2 where n = logical cores.
rem     Preset        16-core   28-core   52-core
rem     quick           5 s       2 s       8 s
rem     baseline       30 s      40 s      2 min
rem     publication   3 min     11 min    40 min
rem
rem  Default = baseline: it's the repo's own recommended setting, and it
rem  scales to large systems without long waits. On Windows with VBS/Hyper-V
rem  (where RDTSC falls back to QPC at ~100ns), use 'publication' to push
rem  timer quantization below the signal.
rem =========================================================================

rem --- paths anchored at this file's folder (safe for double-click launch)
set "ROOT=%~dp0"
set "EXE=%ROOT%bin\core-to-core-latency.exe"
set "PLOT_PY=%ROOT%tools\plot_heatmap.py"
set "DATA=%ROOT%data"
set "PLOTS=%ROOT%plots"

rem --- defaults (repo-recommended baseline; scales to 52+ cores)
set "ITERS=5000"
set "SAMPLES=300"
set "PRESET=baseline"

rem --- per-cell annotation threshold (override via env var; default = always annotate)
if not defined ANNOT_MAX set "ANNOT_MAX=9999"

rem --- arg parsing
if /i "%~1"=="quick" (
    set "ITERS=1000"
    set "SAMPLES=100"
    set "PRESET=quick"
) else if /i "%~1"=="baseline" (
    set "ITERS=5000"
    set "SAMPLES=300"
    set "PRESET=baseline"
) else if /i "%~1"=="publication" (
    set "ITERS=30000"
    set "SAMPLES=1000"
    set "PRESET=publication"
) else if not "%~2"=="" (
    set "ITERS=%~1"
    set "SAMPLES=%~2"
    set "PRESET=custom"
)

rem --- preflight
if not exist "%EXE%"     ( echo [ERROR] missing: %EXE% & goto :end_fail )
if not exist "%PLOT_PY%" ( echo [ERROR] missing: %PLOT_PY% & goto :end_fail )
where py >nul 2>&1      || ( echo [ERROR] py launcher not found. Install Python from python.org & goto :end_fail )
if not exist "%DATA%"  mkdir "%DATA%"  >nul 2>&1
if not exist "%PLOTS%" mkdir "%PLOTS%" >nul 2>&1

rem --- timestamped output tag so repeated runs don't overwrite
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "TS=%%t"
set "TAG=%PRESET%_%ITERS%x%SAMPLES%_%TS%"
set "CSV=%DATA%\%TAG%.csv"
set "PNG=%PLOTS%\%TAG%.png"

rem --- rough runtime estimate (seconds): ~0.00009 * iters * samples * pairs,
rem     where pairs = n*(n-1)/2. We query core count via WMIC.
for /f %%n in ('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum"') do set "NCORES=%%n"
set /a PAIRS=%NCORES% * (%NCORES% - 1) / 2
set /a ETA_S=%ITERS% * %SAMPLES% * %PAIRS% / 11000000
if %ETA_S% LSS 1 set "ETA_S=1"

echo.
echo === core-to-core latency benchmark ===
echo preset       : %PRESET%
echo cores        : %NCORES% logical  (%PAIRS% pairs to measure)
echo iterations   : %ITERS% per sample
echo samples      : %SAMPLES%
echo est. runtime : ~%ETA_S% seconds
echo csv output   : %CSV%
echo png output   : %PNG%
echo.
echo Benchmarking...

rem --- run benchmark; redirect stdout via cmd to keep clean ASCII
"%EXE%" %ITERS% %SAMPLES% --csv > "%CSV%"
if errorlevel 1 ( echo [ERROR] benchmark failed & goto :end_fail )

echo.
echo Plotting heatmap...
py "%PLOT_PY%" "%CSV%" -o "%PNG%" --title "Core-to-core latency (%PRESET%: %ITERS%x%SAMPLES%)" --iters %ITERS% --samples %SAMPLES% --annot-max %ANNOT_MAX%
if errorlevel 1 ( echo [ERROR] plot failed & goto :end_fail )

echo.
echo Done. Opening heatmap...
start "" "%PNG%"

rem --- only pause if launched by double-click (no parent cmd /k), so
rem     interactive CLI users aren't nagged.
echo.%CMDCMDLINE% | findstr /i /c:"/c " >nul
if not errorlevel 1 pause
exit /b 0

:end_fail
echo.
echo.%CMDCMDLINE% | findstr /i /c:"/c " >nul
if not errorlevel 1 pause
exit /b 1
