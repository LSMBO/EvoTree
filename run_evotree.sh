#!/bin/bash
echo "================================================"
echo "              EvoTree Launcher"
echo "    Phylogenetic Analysis Tool"
echo "================================================"
echo ""

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "ERROR: Conda is not installed or not in PATH"
    echo "Please install Miniconda or Anaconda first"
    echo "Download from: https://docs.conda.io/projects/miniconda/en/latest/"
    read -p "Press any key to continue..."
    exit 1
fi

# Check if evotree environment exists
if ! conda info --envs | grep -q "evotree"; then
    echo "ERROR: evotree conda environment not found"
    echo "Please run the installation first:"
    echo "conda env create -f environment.yml"
    read -p "Press any key to continue..."
    exit 1
fi

# Activate environment and run EvoTree
echo "Activating evotree environment..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate evotree

echo "Starting EvoTree application..."
echo "The application will open in your web browser automatically"
echo "Press Ctrl+C to stop EvoTree"
echo ""
echo "================================================"
python main.py

echo ""
echo "EvoTree has been stopped."
read -p "Press any key to continue..."
