"""
mdar -- Markdown Archiver

Archives text files within a markdown file with each enclosed file
occupying its own code block. It supports any number of backticks
embedded in the files being enclosed.

mdar -[cxt] [-X <exclusions>] [-f <mdar-file>] [-C <root-dir>] [<input-file>...]

Create, extract, or list files from a markdown archive (mdar) file

Operating Mode:               Only one mode per invocation.

  -c, --create                Create
  -x, --extract               Extract contents
  -t, --list                  List contents

Options:

  -X, --exclude <exclusions>  File with names to exclude
  -f, --file <mdar-file>      Specify MDARFILE name or "-" for stdin
  -O, --stdout                Extract to stdout
  -C, --chdir <dir>           Change to directory <dir> immediately
  -v, --verbose               Verbose output

"""

import os
from pathlib import Path
import re
import sys
import toml

from docopt import docopt

def get_version():
    pyproject = toml.load(Path(__file__).parent.parent / 'pyproject.toml')
    return pyproject['tool']['poetry']['version']

def determine_backticks(content):
    matches = re.findall(r'`+', content)
    if matches:
        max_backticks = max(len(match) for match in matches)
        return '`' * (max_backticks + 1)
    return '```'

def create_archive(input_files, archive_file, exclusions=None):
    with open(archive_file, 'w') as outfile:
        outfile.write("mdar v0.1.0\n")
        for file_path in input_files:
            if exclusions and file_path in exclusions:
                continue
            with open(file_path, 'r') as infile:
                content = infile.read()
                backticks = determine_backticks(content)
                outfile.write(f"{file_path}\n")
                outfile.write(f"{backticks}\n")
                outfile.write(content)
                outfile.write(f"\n{backticks}\n")
        outfile.write("mdar:index-start\n")
        outfile.write(f"file-count: {len(input_files)}\n")
        for file_path in input_files:
            file_size = os.path.getsize(file_path)
            outfile.write(f"{file_size}\n")
        outfile.write("mdar:index-done\n")

def extract_archive(archive_file, output_dir, to_stdout=False):
    with open(archive_file, 'r') as infile:
        lines = infile.readlines()

    header = lines[0].strip()
    if header != "mdar v0.1.0":
        raise ValueError("Invalid archive format")

    index_start = lines.index("mdar:index-start\n")
    index_end = lines.index("mdar:index-done\n")

    file_metadata = lines[index_start + 1:index_end]
    file_count_line = file_metadata[0]
    file_count = int(file_count_line.split(":")[1].strip())

    file_sizes = [int(size.strip()) for size in file_metadata[1:]]

    current_line = 1
    for _ in range(file_count):
        file_path = lines[current_line].strip()
        backticks_line = current_line + 1
        backticks = lines[backticks_line].strip()
        file_start = backticks_line + 1
        file_end = lines.index(f"{backticks}\n", file_start)

        file_content = "".join(lines[file_start:file_end])

        if to_stdout:
            sys.stdout.write(f"{file_path}:\n{file_content}\n")
        else:
            output_path = Path(output_dir) / file_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as outfile:
                outfile.write(file_content)

        current_line = file_end + 2

def list_archive_contents(archive_file):
    with open(archive_file, 'r') as infile:
        lines = infile.readlines()

    index_start = lines.index("mdar:index-start\n")
    index_end = lines.index("mdar:index-done\n")

    file_metadata = lines[index_start + 1:index_end]
    file_count_line = file_metadata[0]
    file_count = int(file_count_line.split(":")[1].strip())

    print(f"Archive contains {file_count} files:")
    for size_line in file_metadata[1:]:
        print(size_line.strip())

def main(argv = sys.argv[1:]):
    args = docopt(__doc__, argv=argv, version=f'mdar {get_version()}')

    archive_file = args['--file'] or 'archive.mdar'
    input_files = args['<input-file>']
    if args['--exclude']:
        with open(args['--exclude'], 'r') as f:
            exclusions = f.read().splitlines()
    else:
        exclusions = None

    if args['--chdir']:
        os.chdir(args['--chdir'])

    if args['--create']:
        create_archive(input_files, archive_file, exclusions)
    elif args['--extract']:
        extract_archive(archive_file, '.', args['--stdout'])
    elif args['--list']:
        list_archive_contents(archive_file)

if __name__ == "__main__":
    main()
