#!/usr/bin/env python3

import argparse
import difflib
import re
import subprocess
import sys
import io
import shlex


class CodeFormatter(object):
    def __init__(self, binary, line_format, options):
        self.binary = binary
        self.line_format = line_format
        self.options = options

    def format_code(self, lines_by_file, inplace, options, dryrun):
        # Reformat files containing changes in place.
        for filename, lines in lines_by_file.items():
            start_lines, end_lines = zip(*lines)
            line_args = list(
                map(self.line_format.format, start_lines, end_lines))

            command = [self.binary]

            if inplace:
                command.append('-i')
            if options is not None:
                command.extend(options)

            command.extend(line_args)
            command.append(filename)
            command = shlex.split(' '.join(command))

            if not dryrun:
                with subprocess.Popen(
                        command,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE) as proc:

                    stdout, stderr = proc.communicate()
                    if proc.returncode != 0:
                        sys.stderr.write(stderr.decode('UTF-8'))
                        sys.exit(proc.returncode)

                if not inplace:
                    with open(filename) as original:
                        original_code = original.readlines()
                    formatted_code = io.StringIO(
                        stdout.decode('UTF-8')).readlines()
                    diff = difflib.unified_diff(
                        original_code, formatted_code, filename, filename,
                        '(before formatting)', '(after formatting)')
                    diff_string = ''.join(diff)
                    if len(diff_string) > 0:
                        sys.stdout.write(diff_string)
            else:
                print(' '.join(command))


def main():
    parser = argparse.ArgumentParser(
        description=
        'Wrapper in order to pipe git diffs to a formatter. E.g.: git diff '
        '-U0 --no-color HEAD -- /path/to/file.py | python3 git-format-diff.py '
        'yapf -p1 -i')

    parser.add_argument(
        '-i',
        action='store_true',
        default=False,
        help='apply edits to files instead of displaying a diff')
    parser.add_argument('-n', '--dry-run', action='store_true', default=False)
    parser.add_argument('FORMATTER', nargs=1, help='Formatter binary')
    parser.add_argument(
        '-p',
        metavar='NUM',
        default=0,
        help='strip the smallest prefix containing P slashes')
    parser.add_argument(
        '-o',
        '--options',
        nargs='*',
        help='Arguments forwarded to the formatter')
    args = parser.parse_args()

    if args.FORMATTER[0] == 'clang-format':
        formatter = CodeFormatter('clang-format', '-lines={:d}:{:d}',
                                  args.options)
        supported_files = r'.*\.(cpp|cc|c\+\+|cxx|c|cl|h|hpp|m|mm|inc|js|ts|proto|protodevel|java)'
    elif args.FORMATTER[0] == 'yapf':
        formatter = CodeFormatter('yapf', '--lines {:d}-{:d}', args.options)
        supported_files = r'.*\.(py)'
    elif args.FORMATTER[0] == 'yapf3':
        formatter = CodeFormatter('yapf3', '--lines {:d}-{:d}', args.options)
        supported_files = r'.*\.(py)'
    else:
        print("Formatter {} not implemented".format(args.FORMATTER[0]))
        sys.exit(78)

    # Extract changed lines for each file.
    filename = None
    lines_by_file = {}

    for line in sys.stdin:
        match = re.search(r'^\+\+\+\ (.*?/){%s}(\S*)' % args.p, line)
        if match:
            filename = match.group(2)
        if filename is None:
            continue
        if not re.match('^%s$' % supported_files, filename, re.IGNORECASE):
            continue

        match = re.search(r'^@@.*\+(\d+)(,(\d+))?', line)
        if match:
            start_line = int(match.group(1))
            line_count = 1
            if match.group(3):
                line_count = int(match.group(3))
            if line_count == 0:
                continue
            end_line = start_line + line_count - 1
            lines_by_file.setdefault(filename, []).append(
                (start_line, end_line))

    formatter.format_code(lines_by_file, args.i, args.options, args.dry_run)


if __name__ == '__main__':
    main()
