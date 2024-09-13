import os
import sys
import argparse
import re
import tiktoken
import subprocess
import json
import logging
from tqdm import tqdm
from pathlib import Path
from typing import List, Dict, Tuple

def setup_logging(log_file: str):
    logging.basicConfig(filename=log_file, level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        filemode='w')

def clone_repository(repo_url: str, target_dir: str) -> None:
    logging.info(f"Cloning repository: {repo_url} to {target_dir}")
    subprocess.run(["git", "clone", repo_url, target_dir], check=True)
    logging.info("Repository cloned successfully")

def count_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def should_include_file(file_path: str, file_size: int, params: Dict) -> bool:
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in params['exclude_extensions']:
        logging.debug(f"Excluded file due to extension: {file_path}")
        return False
    
    if ext == '.json' and file_size > params['json_size_threshold']:
        logging.debug(f"Excluded JSON file due to size: {file_path}")
        return False
    
    if file_size > params['max_file_size']:
        logging.debug(f"Excluded file due to size: {file_path}")
        return False
    
    return True

def process_directory(
    path: str,
    current_depth: int,
    params: Dict,
    output_file,
    excluded_files: List[Tuple[str, int]]
) -> None:
    if current_depth > params['max_depth']:
        logging.debug(f"Max depth reached: {path}")
        return

    items = sorted(os.listdir(path))
    
    for item in items:
        item_path = os.path.join(path, item)
        
        if any(re.match(pattern, item_path) for pattern in params['ignore_patterns']):
            logging.debug(f"Ignored item due to pattern: {item_path}")
            output_file.write(f"{'  ' * current_depth}└── {item}/ [Ignored]\n")
            continue
        
        if os.path.isdir(item_path):
            output_file.write(f"{'  ' * current_depth}└── {item}/\n")
            if item not in params['no_traverse_dirs']:
                process_directory(item_path, current_depth + 1, params, output_file, excluded_files)
            else:
                logging.debug(f"Directory not traversed: {item_path}")
        else:
            file_size = os.path.getsize(item_path)
            
            if should_include_file(item_path, file_size, params):
                output_file.write(f"{'  ' * current_depth}├── {item}\n")
                
                try:
                    with open(item_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if count_tokens(content) <= params['token_limit']:
                        output_file.write(f"{'  ' * (current_depth + 1)}Content:\n")
                        output_file.write(f"{content}\n\n")
                    else:
                        output_file.write(f"{'  ' * (current_depth + 1)}[Content excluded due to token limit]\n\n")
                        logging.info(f"Content excluded due to token limit: {item_path}")
                except Exception as e:
                    logging.error(f"Error processing file {item_path}: {str(e)}")
                    output_file.write(f"{'  ' * (current_depth + 1)}[Error processing file]\n\n")
            else:
                output_file.write(f"{'  ' * current_depth}├── {item} [Excluded]\n")
                excluded_files.append((item_path, file_size))

def main():
    parser = argparse.ArgumentParser(description="Process a GitHub repository or local directory")
    parser.add_argument("path", help="URL of the GitHub repository or path to local directory")
    parser.add_argument("--token-limit", type=int, default=1000, help="Token limit for non-code text files")
    parser.add_argument("--json-size-threshold", type=int, default=1024*1024, help="Size threshold for JSON files (in bytes)")
    parser.add_argument("--exclude-extensions", nargs='+', default=['.csv', '.pt', '.pkl', '.bin', '.h5', '.parquet'], help="File extensions to exclude")
    parser.add_argument("--ignore-patterns", nargs='+', default=['node_modules', '.git', '__pycache__'], help="Directories or file patterns to ignore")
    parser.add_argument("--max-depth", type=int, default=10, help="Maximum depth for directory tree processing")
    parser.add_argument("--max-file-size", type=int, default=10*1024*1024, help="Maximum file size to include (in bytes)")
    parser.add_argument("--output", default="repo_structure.txt", help="Output file name")
    parser.add_argument("--split-threshold", type=int, default=1000000, help="Token threshold for splitting output files")
    parser.add_argument("--log-file", default="repo_processing.log", help="Log file name")
    parser.add_argument("--no-traverse-dirs", nargs='+', default=['node_modules', '__pycache__'], help="Directories to list but not traverse")
    
    args = parser.parse_args()
    
    setup_logging(args.log_file)
    logging.info("Starting repository/directory processing")
    
    params = vars(args)
    
    if args.path.startswith(('http://', 'https://', 'git://')):
        temp_dir = "temp_repo"
        clone_repository(args.path, temp_dir)
        process_path = temp_dir
    else:
        process_path = args.path
    
    excluded_files = []
    output_files = []
    current_file = 1
    current_tokens = 0
    
    output_file = open(f"{args.output}", 'w', encoding='utf-8')
    output_files.append(output_file.name)
    
    logging.info("Processing repository/directory structure")
    process_directory(process_path, 0, params, output_file, excluded_files)
    
    logging.info("Listing excluded files")
    for file_path, size in excluded_files:
        logging.info(f"Excluded: {file_path} - {size} bytes")
    
    output_file.close()
    
    logging.info("Estimating total token count")
    total_tokens = 0
    for file_name in output_files:
        with open(file_name, 'r', encoding='utf-8') as f:
            content = f.read()
            file_tokens = count_tokens(content)
            total_tokens += file_tokens
            logging.info(f"{file_name}: {file_tokens} tokens")
    
    logging.info(f"Total tokens: {total_tokens}")
    
    if total_tokens > args.split_threshold:
        logging.info("Output exceeds split threshold. Splitting into multiple files.")
        split_files = []
        current_tokens = 0
        current_content = ""
        part = 1
        
        for file_name in output_files:
            with open(file_name, 'r', encoding='utf-8') as f:
                content = f.read()
                content_tokens = count_tokens(content)
                
                if current_tokens + content_tokens > args.split_threshold:
                    split_file_name = f"{args.output}.split{part}"
                    with open(split_file_name, 'w', encoding='utf-8') as split_f:
                        split_f.write(current_content)
                    split_files.append(split_file_name)
                    logging.info(f"Created split file: {split_file_name}")
                    part += 1
                    current_content = content
                    current_tokens = content_tokens
                else:
                    current_content += content
                    current_tokens += content_tokens
        
        if current_content:
            split_file_name = f"{args.output}.split{part}"
            with open(split_file_name, 'w', encoding='utf-8') as split_f:
                split_f.write(current_content)
            split_files.append(split_file_name)
            logging.info(f"Created final split file: {split_file_name}")
        
        logging.info(f"Output split into {len(split_files)} files")
    
    logging.info("Processing complete")

if __name__ == "__main__":
    main()
