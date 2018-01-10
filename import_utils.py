#!/usr/bin/env python3

"""
Utilities related to module imports and import statements.

Should work in both Python 2 and 3.
"""

import argparse
import ast
import copy
import logging
import os
import pkgutil
import sys



class ImportLister(ast.NodeVisitor):
    def __init__(self):
        self._imports = []

    @property
    def imports(self):
        return copy.copy(self._imports)

    def _inspect_module_import(self, node):
        for name in node.names:
            if '.' in name.name:
                # Only keep the module name before the first period
                self._imports.append(name.name.split('.', 1)[0])
            else:
                self._imports.append(name.name)

    def visit_Import(self, node):
        self._inspect_module_import(node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self._inspect_module_import(node)
        self.generic_visit(node)



def get_filepaths(files_or_directories):
    filepaths = []
    for thing in files_or_directories:
        isfile = os.path.isfile(thing)
        assert isfile or os.path.isdir(thing), (
            'file_or_directory argument must be an existing file or directory'
        )

        if isfile:
            filepaths.append(thing)
        else:
            for root, _, filenames in os.walk(thing):
                for filename in filenames:
                    filepaths.append(os.path.join(root, filename))

    return filepaths



def collect_non_builtins(imports, include_installed):
    non_builtin_mods = []
    builtin_modules = set(list(sys.builtin_module_names) +
                          [mod[1] for mod in pkgutil.iter_modules()])

    for mod_import in imports:
        if include_installed or mod_import not in builtin_modules:
            non_builtin_mods.append(mod_import)

    return non_builtin_mods



def display_imports(mods_to_display):
    print('Libraries imported:')
    for mod in sorted(mods_to_display):
        print('    {}'.format(mod))



def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('file_or_directory', nargs='+', help=(
        'One or more files/directories containing Python code to parse'
    ))
    parser.add_argument('-x', '--exclude-installed', action='store_true', help=(
        'Exclude installed libraries / all modules which can already be '
        'imported'
    ))
    parser.add_argument('-d', '--debug', action='store_true', help=(
        'Print debugging statements'
    ))
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    filepaths = get_filepaths(args.file_or_directory)

    logging.debug('Parsing {} files...'.format(len(filepaths)))

    import_lister = ImportLister()
    for filepath in filepaths:
        with open(filepath, 'r') as fp:
            tree = ast.parse(fp.read())
            import_lister.visit(tree)

    imports = import_lister.imports
    logging.debug('Found {} imports...'.format(len(imports)))

    mods_to_display = collect_non_builtins(imports, not args.exclude_installed)

    if mods_to_display:
        display_imports(mods_to_display)



if __name__ == '__main__':
    sys.exit(main(sys.argv))
