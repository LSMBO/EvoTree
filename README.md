# EvoTree - Phylogenetic Analysis Tool

A web-based application for phylogenetic analysis using NCBI and UniProt databases. EvoTree allows you to search for proteins and genes, perform sequence alignments, and construct phylogenetic trees through an intuitive web interface.

## Features

- **Protein Search**: Query proteins from UniProt and NCBI databases
- **Gene Search**: Search for mRNA sequences from NCBI Nucleotide database  
- **Sequence Selection**: Filter sequences by length, database, and other criteria
- **Phylogenetic Pipeline**: Automated sequence alignment (MAFFT) and tree construction (IQ-TREE)
- **Export Options**: Download FASTA files and phylogenetic results

## Installation

### Prerequisites

1. **Install Miniconda or Anaconda**
   - Download from: https://docs.conda.io/projects/miniconda/en/latest/
   - Follow the installation instructions for your operating system
   - Make sure conda is added to your system PATH

### Setup Instructions

1. **Download the source code**
   - Click on the green **"Code"** button
   - Select **"Download ZIP"**
   - Extract the ZIP file

2. **Open Anaconda Prompt**
   - Navigate to the EvoTree folder you just extracted
   ```bash
   cd C:\EvoTree\
   ```

3. **Create the conda environment**
   ```bash
   conda env create -f environment.yml
   ```
   This will create a new conda environment called `evotree` with all required dependencies.

4. **Verify installation**
   ```bash
   conda activate evotree
   python --version  # Should show Python 3.11.x
   ```

## Usage

### Starting EvoTree

**Option 1: Using the batch file (Windows)**
- Simply double-click `run_evotree.bat`
- The application will start automatically and open in your web browser

**Option 2: Manual startup**
```bash
conda activate evotree
python main.py
```

### Using the Application

1. **Search for sequences**:
   - Enter a protein or gene name
   - Specify taxonomy (organism name or ID)
   - Choose between protein search (UniProt + NCBI) or gene search (NCBI mRNA)

2. **Select and filter sequences**:
   - Review results in the interactive table
   - Apply filters by sequence length, database, or mRNA availability
   - Select sequences for phylogenetic analysis

3. **Run phylogenetic analysis**:
   - Click "Build Phylogenetic Tree" to start the automated pipeline
   - The system will perform sequence alignment and tree construction
   - Download results including FASTA files, alignments, and phylogenetic trees

### Stopping EvoTree

- Close the terminal/command prompt window, or
- Press `Ctrl+C` in the terminal

## System Requirements

- **Operating System**: Windows, macOS, or Linux
- **Python**: 3.11+ (automatically installed with conda environment)
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Disk Space**: 2GB free space for installation
- **Internet**: Required for database queries (NCBI, UniProt)

## Dependencies

### Main Dependencies
- **NiceGUI**: Web-based user interface
- **BioPython**: Biological sequence analysis
- **Requests/HTTPX**: HTTP client for API calls
- **NumPy/SciPy**: Numerical computing
- **Matplotlib**: Plotting and visualization

### External Tools (Server-side)
- **MAFFT**: Multiple sequence alignment
- **IQ-TREE**: Maximum-likelihood phylogenetic inference
- **BMGE**: Block mapping and gathering with entropy (optional)

## Troubleshooting

### Common Issues
**1. Conda environment creation fails**
```bash
# Try with explicit solver
conda env create -f environment.yml --solver=classic
```

**2. Application doesn't start**
- Verify conda environment is activated: `conda activate evotree`
- Check if all dependencies are installed: `conda list`
- Try running directly: `python main.py`

**3. Browser doesn't open automatically**
- Manually navigate to: http://localhost:8080
- Check if port 8080 is available

**4. Database connection issues**
- Verify internet connection
- Check if NCBI/UniProt services are accessible

**5. Server connection issues**
- If requests fail, the Flask server might be under maintenance. Please try again later.
- If the issue persists, contact me for further assistance.

## Contact

For questions or support, please contact:
- **Email**: browna@unistra.fr
- **GitHub**: [LSMBO/EvoTree](https://github.com/LSMBO/EvoTree)
