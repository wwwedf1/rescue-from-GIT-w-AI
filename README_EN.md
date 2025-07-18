# Git Object Recovery and Analysis Tool

A simple and easy-to-use Git object extraction and analysis tool that helps you recover files from `.git` directories and perform intelligent analysis.

## 🎯 Main Features

- **File Recovery**: Extract all file contents from `.git/objects`
- **Smart Filtering**: Use AI models to automatically identify valuable files (AI is not strictly necessary for this step, but non-AI identification is not yet implemented)
- **Version Organization**: AI infers version history of the same file and organizes them
- **Graphical and Command Line Interfaces**, long file processing

## 🚀 Quick Start

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Graphical Interface
```bash
python run_gui.py
```

**Note**: The GUI interface calls command-line tools, and all execution output will be displayed in the system terminal for real-time progress monitoring and debugging.

### Command Line Usage

#### One-Click Processing (Recommended)
```bash
# Use default time range (2 AM today to now)
python main.py full --git-dir "D:\repo\.git" 

# Specify time range
python main.py full --git-dir "D:\repo\.git" --start-time "2024-07-15 02:00" --end-time "2024-12-31 23:59" 

# Fast mode (one-time grouping + parallel comparison)
python main.py full --git-dir "D:\repo\.git" --fast 
```

#### Step-by-Step Processing
```bash
# Extract files only
python main.py extract --git-dir "D:\repo\.git" --start-time "2024-07-15 02:00"

# AI analysis only
python main.py analyze 

# Version grouping only
python main.py group 

# Version comparison and organization only
python main.py compare 

# Iteration mode (perform iterative version analysis on analyzed_files)
python main.py iterate 
```

## 📋 Command Reference

### Subcommands

- **`extract`** - Extract files from Git objects
  - Required parameters: `--git-dir`
  - Optional parameters: `--start-time`, `--end-time`

- **`analyze`** - Perform AI analysis on extracted files
  - Optional parameters: `--input-dir` (default: extracted_objects)

- **`group`** - Perform version grouping based on analysis results
  - Optional parameters: `--input-dir` (default: analyzed_files)

- **`compare`** - Perform version comparison and organize files
  - Optional parameters: `--input-dir` (default: grouped_files)

- **`full`** - Execute complete workflow: extract→analyze→group→compare
  - Optional parameters: `--git-dir`, `--fast` (fast mode)

- **`iterate`** - Perform iterative version analysis on analyzed_files
  - Optional parameters: `--input-dir` (default: analyzed_files)

- **`config`** - Configuration management
  - Usage: `python main.py config save <config_file_path>`

### Common Parameters

- `--ai-model` - AI model (default: moonshot)
- `--api-key` - API key
- `--max-workers` - Concurrency level (default: 50)
- `--config-file` - Configuration file path (default: config.ini)

### Output Directory Parameters

- `--extract-output` - Extraction output directory (default: extracted_objects)
- `--analyze-output` - AI analysis output directory (default: analyzed_files)
- `--grouped-output` - Version grouping output directory (default: grouped_files)
- `--organized-output` - Version organization output directory (default: organized_files)

## 🖥️ GUI Interface Guide

The GUI interface provides the following features:

### Single-Step Operations
- **Extract Objects** - Execute `extract` command
- **AI Analysis** - Execute `analyze` command  
- **Version Grouping** - Execute `group` command
- **Version Comparison and Organization** - Execute `compare` command
- **Iterative Version Analysis** - Execute `iterate` command

### One-Click Operations
- **Fast One-Click** - Execute `full --fast` command
- **Standard One-Click** - Execute `full` command

### Real-Time Output
- GUI calls command-line tools, and all execution output is displayed in the system terminal
- You can monitor progress, error messages, and debug output in real-time in the terminal
- GUI log area displays command execution status and results

## ⚙️ Configuration Guide

### Time Parameters
- **No time specified**: Default to "2 AM today to now"
- **Start time only**: End time automatically set to "now"
- **End time only**: Start time set to January 1, 2000
- **Both specified**: Strictly follow user-specified time range

Time format: `YYYY-MM-DD HH:MM`, e.g.: `2024-07-15 02:00`

### AI Model Configuration
Configure your AI models in `config.ini`:
```ini
[ai_models]
moonshot = https://api.moonshot.cn/v1
openai = https://api.openai.com/v1
```

### Output Directories
- `extracted_objects/` - Extracted original files
- `analyzed_files/` - AI-filtered valuable files
- `grouped_files/` - Version grouping results
- `organized_files/` - Final organized files

## 📁 Output File Structure

### Extraction Results
```
extracted_objects/
├─ <object-id>.txt       # File content for each Git object
└─ extraction_log.json   # Extraction process log
```

### AI Analysis Results
```
analyzed_files/
├─ valuable_<n>.txt      # Files considered valuable by AI
└─ analysis_report.json  # Analysis report and reasoning
```

### Version Grouping Results
```
grouped_files/
├─ version_groups.json   # Version grouping report
└─ group_001_组名/      # Group directories (enabled by default)
    ├─ file1_hash.txt
    ├─ file2_hash.txt
    └─ ...
```

### Version Organization Results
```
organized_files/
├─ <filename> /          # Grouped directories
│  ├─ <filename>                    # Latest version file
│  ├─ <filename> 版本分析报告.json   # Version analysis report for this file
│  └─ old/                          # Historical versions directory
│     ├─ <filename>_<hash>.md       # Historical version files
│     └─ ...
└─ version_analysis_report.json     # Overall version analysis report
```

## 🔧 Advanced Configuration

### Concurrency Control
```bash
python main.py full --git-dir "D:\repo\.git" --max-workers 3 --ai-model moonshot
```

### Mode Selection
```bash
# Stable mode (default): Iterative grouping + serial comparison
python main.py full --git-dir "D:\repo\.git" --ai-model moonshot

# Fast mode: One-time grouping + parallel comparison
python main.py full --git-dir "D:\repo\.git" --fast --ai-model moonshot

# Iteration mode: Perform iterative version analysis on analyzed_files
python main.py iterate --input-dir "analyzed_files" --ai-model moonshot
```

**Q: What's the difference between fast mode and stable mode?**
A: Fast mode uses one-time grouping, which is faster but may be less accurate; stable mode uses iterative grouping, which is more accurate but slower.

## 📄 License

Code is generated by AI, main functionality is basically usable, but there may be many small issues and unnecessary redundancies. 