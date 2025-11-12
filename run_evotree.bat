@echo off
echo ================================================
echo              EvoTree Launcher
echo    Phylogenetic Analysis Tool
echo ================================================
echo.

REM Check if conda is available
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Conda is not installed or not in PATH
    echo Please install Miniconda or Anaconda first
    echo Download from: https://docs.conda.io/projects/miniconda/en/latest/
    pause
    exit /b 1
)

REM Check if evotree environment exists
conda info --envs | findstr "evotree" >nul
if %errorlevel% neq 0 (
    echo ERROR: evotree conda environment not found
    echo Please run the installation first:
    echo conda env create -f environment.yml
    pause
    exit /b 1
)

REM Activate environment and run EvoTree
echo Activating evotree environment...
call conda activate evotree

echo Starting EvoTree application...
echo The application will open in your web browser automatically
echo Close this window to stop EvoTree
echo.
echo ================================================
python main.py

echo.
echo EvoTree has been stopped.
pause