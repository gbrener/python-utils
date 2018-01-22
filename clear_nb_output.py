#!/usr/bin/env python

"""
An untested script which (should) clear all notebook cells and execution
counts.

Should work in both Python 2 and Python 3.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys
import argparse
import json
import copy
import os


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('src_fpath', help='File path to notebook file (.ipynb) to be cleared.')
    parser.add_argument('-o', '--output', help='Output file to write resulting notebook. If not provided, output will be writen to STDOUT.')
    args = parser.parse_args()

    with open(args.src_fpath, 'rb') as src_fp:
        src_json = json.load(src_fp)
    dest_json = copy.deepcopy(src_json)

    for cell in dest_json['cells']:
        if 'execution_count' in cell or cell['cell_type'] == 'code':
            cell['execution_count'] = None
        if 'outputs' in cell or cell['cell_type'] == 'code':
            cell['outputs'] = []

    if args.output is not None:
        parent_dpath = os.path.dirname(args.output)
        if not os.path.isdir(parent_dpath):
            os.makedirs(parent_dpath)
        with open(args.output, 'w') as dest_fp:
            json.dump(dest_json, dest_fp, indent=4, allow_nan=False)
    else:
        print(json.dumps(dest_json, indent=4, allow_nan=False))


if __name__ == '__main__':
    sys.exit(main(sys.argv))
