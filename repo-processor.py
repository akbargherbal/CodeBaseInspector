import os
import sys
import argparse
import re
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Tuple

def setup_logging(log_file: str):
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filemode="w",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)


default_excluded_folders = [".git", "node_modules", "__pycache__", "theme", "CLAUDE_THEMES", "MY_LEARNING", "idx_customization", "TODO"]
default_excluded_extensions = [".csv", ".pt", ".pkl", ".bin", ".h5", ".parquet", ".png", ".ico", ".jpg", ".svg", ".sqlite3", ".code-profile", ".ipynb", ".mermaid", ".xlsx", ".docx"]
def clone_repository(repo_url: str, target_dir: str) -> None:
    logging.info(f"Cloning repository: {repo_url} to {target_dir}")
    subprocess.run(["git", "clone", repo_url, target_dir], check=True)
    logging.info("Repository cloned successfully")

def clear_directory_cache(path: str):
    try:
        os.scandir(path).close()
    except:
        pass

def should_include_file(file_path: str, file_size: int, params: Dict) -> bool:
    ext = Path(file_path).suffix.lower()
    
    if ext in params["exclude_extensions"]:
        logging.debug(f"Excluded file due to extension: {file_path}")
        return False
    
    if file_size > params["max_file_size"]:
        logging.debug(f"Excluded file due to size: {file_path}")
        return False
    
    return True

def process_directory(
    path: str,
    current_depth: int,
    params: Dict,
    output_file,
    excluded_files: List[Tuple[str, int]],
) -> None:
    if current_depth > params["max_depth"]:
        logging.debug(f"Max depth reached: {path}")
        return

    clear_directory_cache(path)
    items = sorted(os.scandir(path), key=lambda e: e.name)

    for item in items:
        if item.name in params["ignore_patterns"] or any(
            re.match(pattern, item.path) for pattern in params["ignore_patterns"]
        ):
            logging.info(f"Ignored item: {item.path}")
            output_file.write(f"{'  ' * current_depth}└── {item.name}/ [Ignored]\n")
            continue

        if item.is_dir():
            output_file.write(f"{'  ' * current_depth}└── {item.name}/\n")
            if item.name not in params["no_traverse_dirs"]:
                process_directory(
                    item.path, current_depth + 1, params, output_file, excluded_files
                )
            else:
                logging.info(f"Directory not traversed: {item.path}")
        else:
            if should_include_file(item.path, item.stat().st_size, params):
                output_file.write(f"{'  ' * current_depth}├── {item.name}\n")
                try:
                    with open(item.path, "r", encoding="utf-8") as f:
                        content = f.read()
                    output_file.write(f"{'  ' * (current_depth + 1)}Content:\n")
                    output_file.write(f"{content}\n\n")
                except Exception as e:
                    logging.error(f"Error processing file {item.path}: {str(e)}")
                    output_file.write(f"{'  ' * (current_depth + 1)}[Error processing file]\n\n")
            else:
                output_file.write(f"{'  ' * current_depth}├── {item.name} [Excluded]\n")
                excluded_files.append((item.path, item.stat().st_size))

def main():
    parser = argparse.ArgumentParser(description="Process a GitHub repository or local directory")
    parser.add_argument("path", help="URL of the GitHub repository or path to local directory")
    parser.add_argument("--json-size-threshold", type=int, default=1024*1024, help="Size threshold for JSON files (in bytes)")
    parser.add_argument("--exclude-extensions", nargs="+", default=default_excluded_extensions, help="File extensions to exclude")
    parser.add_argument("--ignore-patterns", nargs="+", default=default_excluded_folders, help="Directories or file patterns to ignore")
    parser.add_argument("--max-depth", type=int, default=10, help="Maximum depth for directory tree processing")
    parser.add_argument("--max-file-size", type=int, default=1024*1024, help="Maximum file size to include (in bytes)")
    parser.add_argument("--output", default="repo_structure.txt", help="Output file name")
    parser.add_argument("--log-file", default="repo_processing.log", help="Log file name")
    parser.add_argument("--no-traverse-dirs", nargs="+", default=default_excluded_folders, help="Directories to list but not traverse")

    args = parser.parse_args()
    
    setup_logging(args.log_file)
    logging.info("Starting repository/directory processing")
    
    params = vars(args)
    
    if args.path.startswith(("http://", "https://", "git://")):
        temp_dir = "temp_repo"
        clone_repository(args.path, temp_dir)
        process_path = temp_dir
    else:
        process_path = args.path
    
    excluded_files = []
    
    with open(args.output, "w", encoding="utf-8") as output_file:
        logging.info("Processing repository/directory structure")
        process_directory(process_path, 0, params, output_file, excluded_files)
    
    logging.info("Listing excluded files")
    for file_path, size in excluded_files:
        logging.info(f"Excluded: {file_path} - {size} bytes")
    
    logging.info("Processing complete")

if __name__ == "__main__":
    main()
