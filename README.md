# Repository Processing Scripts

This repository contains two Python scripts designed to clone GitHub repositories, analyze their structure, and prepare their contents for use with large language models:

1. `repo-processor.py`: The original script that processes a repository's structure and content.
2. `repo-processor-with-notebooks.py`: An enhanced version that also handles Jupyter notebooks by converting them to Markdown.

## Prerequisites

- Python 3.7 or higher
- Git installed and configured on your system

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/your-username/repo-processing-scripts.git
   cd repo-processing-scripts
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

### repo-processor.py

This script clones a GitHub repository and generates a tree-like structure of its contents, including the code from relevant files.

```
python repo-processor.py <repository_url> [options]
```

Options:
- `--token-limit`: Token limit for non-code text files (default: 1000)
- `--json-size-threshold`: Size threshold for JSON files in bytes (default: 1048576)
- `--exclude-extensions`: File extensions to exclude (default: .csv .pt .pkl .bin .h5 .parquet)
- `--ignore-patterns`: Directories or file patterns to ignore (default: node_modules .git)
- `--max-depth`: Maximum depth for directory tree processing (default: 10)
- `--max-file-size`: Maximum file size to include in bytes (default: 10485760)
- `--output`: Output file name (default: repo_structure.txt)
- `--split-threshold`: Token threshold for splitting output files (default: 1000000)
- `--log-file`: Log file name (default: repo_processing.log)

### repo-processor-with-notebooks.py

This script includes all functionality of `repo-processor.py` and adds support for converting Jupyter notebooks to Markdown.

```
python repo-processor-with-notebooks.py <repository_url> [options]
```

This script accepts the same options as `repo-processor.py`.

## Output

Both scripts generate:
1. A text file (default: `repo_structure.txt`) containing the repository structure and content of included files.
2. A log file (default: `repo_processing.log`) with details about the processing.

If the output exceeds the split threshold, it will be divided into multiple files.

## Examples

Process a repository with default settings:
```
python repo-processor.py https://github.com/username/repo-name
```

Process a repository with custom settings and notebook handling:
```
python repo-processor-with-notebooks.py https://github.com/username/repo-name --token-limit 1500 --max-depth 5 --output my_repo_structure.txt
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
