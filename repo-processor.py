import os
import argparse
import tempfile
import git
import json
import logging
from pathlib import Path

def setup_logging(log_file):
    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

def clone_or_use_local(repo_url_or_path, temp_dir):
    if os.path.isdir(repo_url_or_path):
        # It's a local directory, use it directly
        return repo_url_or_path
    else:
        # It's a URL, clone it
        return git.Repo.clone_from(repo_url_or_path, temp_dir).working_tree_dir

def process_file(file_path, token_limit, json_size_threshold):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            if file_path.suffix == '.json':
                if os.path.getsize(file_path) > json_size_threshold:
                    return "[JSON file larger than threshold]"
                return json.load(file)
            content = file.read()
            if len(content.split()) > token_limit:
                return f"[Content truncated due to token limit. First {token_limit} tokens shown]\n" + ' '.join(content.split()[:token_limit])
            return content
    except Exception as e:
        logging.error(f"Error processing file {file_path}: {str(e)}")
        return f"[Error processing file: {str(e)}]"

def should_exclude(path, exclude_extensions, ignore_patterns, max_file_size):
    if any(pattern in str(path) for pattern in ignore_patterns):
        return True
    if path.is_file():
        if path.suffix in exclude_extensions:
            return True
        if os.path.getsize(path) > max_file_size:
            return True
    return False

def process_directory(path, indent="", depth=0, max_depth=10, **kwargs):
    if depth > max_depth:
        return f"{indent}{path.name}/\n{indent}  [Max depth reached]\n"

    result = f"{indent}{path.name}/\n"
    try:
        for item in sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name)):
            if should_exclude(item, **kwargs):
                continue
            if item.is_dir():
                result += process_directory(item, indent + "  ", depth + 1, max_depth, **kwargs)
            else:
                result += f"{indent}  {item.name}\n"
                content = process_file(item, kwargs['token_limit'], kwargs['json_size_threshold'])
                result += f"{indent}    Content:\n{indent}    {content.replace(chr(10), chr(10) + indent + '    ')}\n\n"
    except Exception as e:
        logging.error(f"Error processing directory {path}: {str(e)}")
        result += f"{indent}  [Error processing directory: {str(e)}]\n"
    return result

def write_output(output, output_file, split_threshold):
    if len(output) > split_threshold:
        base, ext = os.path.splitext(output_file)
        part = 1
        while output:
            with open(f"{base}_part{part}{ext}", 'w', encoding='utf-8') as f:
                f.write(output[:split_threshold])
            output = output[split_threshold:]
            part += 1
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)

def main():
    parser = argparse.ArgumentParser(description="Process a GitHub repository or local directory.")
    parser.add_argument("repo_url_or_path", help="GitHub repository URL or path to local directory")
    parser.add_argument("--token-limit", type=int, default=1000, help="Token limit for non-code text files")
    parser.add_argument("--json-size-threshold", type=int, default=1048576, help="Size threshold for JSON files in bytes")
    parser.add_argument("--exclude-extensions", nargs='+', default=['.csv', '.pt', '.pkl', '.bin', '.h5', '.parquet'], help="File extensions to exclude")
    parser.add_argument("--ignore-patterns", nargs='+', default=['node_modules', '.git'], help="Directories or file patterns to ignore")
    parser.add_argument("--max-depth", type=int, default=10, help="Maximum depth for directory tree processing")
    parser.add_argument("--max-file-size", type=int, default=10*1024*1024, help="Maximum file size to include in bytes")
    parser.add_argument("--output", default="repo_structure.txt", help="Output file name")
    parser.add_argument("--split-threshold", type=int, default=1000000, help="Token threshold for splitting output files")
    parser.add_argument("--log-file", default="repo_processing.log", help="Log file name")

    args = parser.parse_args()

    setup_logging(args.log_file)

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            repo_path = clone_or_use_local(args.repo_url_or_path, temp_dir)
            output = process_directory(
                Path(repo_path),
                max_depth=args.max_depth,
                token_limit=args.token_limit,
                json_size_threshold=args.json_size_threshold,
                exclude_extensions=args.exclude_extensions,
                ignore_patterns=args.ignore_patterns,
                max_file_size=args.max_file_size
            )
            write_output(output, args.output, args.split_threshold)
            logging.info(f"Processing completed. Output written to {args.output}")
        except Exception as e:
            logging.error(f"Error processing repository: {str(e)}")
            print(f"An error occurred. Please check the log file {args.log_file} for details.")

if __name__ == "__main__":
    main()