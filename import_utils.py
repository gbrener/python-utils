#!/usr/bin/env python3

"""
Utilities related to module imports and import statements.
"""

import argparse
import ast
from collections import defaultdict
import copy
import json
import logging
import os
import pkgutil
import re
import sys



class ImportLister(ast.NodeVisitor):
    def __init__(self):
        self.filename = None
        self._imports = defaultdict(list)

    @property
    def imports(self):
        return copy.deepcopy(self._imports)

    def visit_Import(self, node):
        for name in node.names:
            if '.' in name.name:
                # Only keep the module name before the first period
                mod = name.name.split('.', 1)[0]
                self._imports[mod].append((self.filepath, node.lineno, node.col_offset))
            else:
                mod = name.name
                self._imports[mod].append((self.filepath, node.lineno, node.col_offset))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        # Skip relative imports
        if node.level == 0:
            if '.' in node.module:
                # Only keep the module name before the first period
                mod = node.module.split('.', 1)[0]
                self._imports[mod].append((self.filepath, node.lineno, node.col_offset))
            else:
                mod = node.module
                self._imports[mod].append((self.filepath, node.lineno, node.col_offset))
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
                    ext = os.path.splitext(filename.lower())[-1]
                    if ext in ('.py', '.ipynb'):
                        filepaths.append(os.path.join(root, filename))

    return filepaths



def collect_non_builtins(imports, exclude_installable):
    non_builtin_mods = {}
    installable_modules = set(list(sys.builtin_module_names) +
                              [mod[1] for mod in pkgutil.iter_modules()])

    for mod_import, metadata in imports.items():
        if exclude_installable and mod_import in installable_modules:
            continue

        required = any(map(lambda meta: meta[2] == 0, metadata))
        if required:
            non_builtin_mods[mod_import] = {}
        else:
            non_builtin_mods[mod_import] = filter(lambda meta: meta[2] > 0, metadata)

    return non_builtin_mods



def display_imports(mods_to_display):
    print('Imports found ({}):'.format(len(mods_to_display)))
    width = max(map(len, mods_to_display))
    for mod in sorted(mods_to_display):
        info = ', '.join(map(lambda t: ':'.join([str(tx) for tx in t]), mods_to_display[mod]))
        print('    {:{width}}{}'.format(mod, '  # {}'.format(info) if info else '', width=(width if info else '')))



def main(argv):
    parser = argparse.ArgumentParser(description='List Python imports in any number of files / directories passed as arguments (Jupyter notebooks experimentally supported). If the imports appear to be optional - nested in control flow structures like if-statements, try-catch, etc - their locations are displayed as well.')
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

    # Set logging level
    logging.basicConfig(level=(logging.DEBUG if args.debug else logging.INFO))

    filepaths = get_filepaths(args.file_or_directory)

    logging.debug('Parsing {} files...'.format(len(filepaths)))

    import_lister = ImportLister()
    for filepath in filepaths:
        import_lister.filepath = filepath
        with open(filepath, 'rU') as fp:
            logging.debug('Parsing %s', filepath)
            contents = ''
            if filepath.lower().endswith('.ipynb'):
                nb_json = json.load(fp)
                for cell in nb_json['cells']:
                    if cell['cell_type'] == 'code':
                        cell_src = ''.join(cell['source'])
                        if not cell_src.startswith('%%'):
                            contents += cell_src + '\n'
            else:
                contents = fp.read()
            # Remove lines that start with '%' or '!'
            if re.search(r'\n\s*%[a-zA-Z]', contents):
                contents = re.sub(r'\n\s*%[a-zA-Z][^\n]*', '', contents)
            if re.search(r'\n\s*!', contents):
                contents = re.sub(r'\n\s*![^\n]*', '', contents)
            tree = ast.parse(contents)
            import_lister.visit(tree)

    imports = import_lister.imports
    logging.debug('Found {} imports...'.format(sum(map(len, imports.values()))))

    mods_to_display = collect_non_builtins(imports, args.exclude_installed)

    if mods_to_display:
        display_imports(mods_to_display)



if __name__ == '__main__':
    sys.exit(main(sys.argv))
