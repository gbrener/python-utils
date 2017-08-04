#!/usr/bin/env conda-shell
#!conda-shell -i python -c conda-forge python python-graphviz pyyaml

"""
Print an environment.yml file to STDOUT with only the packages required to
reproduce an existing conda environment.

Works with Python 2 and Python 3.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys
import os
import argparse
import subprocess
from collections import defaultdict

import yaml
import graphviz as gv


class PackageSpec(object):
    def __init__(self, name, version, from_pip=False):
        self.name = name
        self.version = version
        self.from_pip = from_pip
        self._deps = None

    @property
    def path(self):
        if self._path is None:
            raise ValueError('Path has not been set for '+repr(self))
        return self._path

    @path.setter
    def path(self, newpath):
        self._path = newpath

    @property
    def channel(self):
        if self._channel is None:
            raise ValueError('Channel has not been set for '+repr(self))
        return self._channel

    @channel.setter
    def channel(self, newchannel):
        self._channel = newchannel

    @property
    def deps(self):
        if self._deps is None:
            return []
        return self._deps

    @deps.setter
    def deps(self, dependencies):
        self._deps = {}
        for dependency in dependencies:
            dep = dependency.split()
            if len(dep) > 2 and dep[-1] == 'openblas':
                self._deps[dep.pop()] = tuple()
            name = dep[0]
            constraints = ()
            if len(dep) > 1:
                constraints = dep[1:]
            self._deps[name] = tuple(constraints)

    def __repr__(self):
        return ('PackageSpec<'
                'name: "{}", '
                'version: "{}", '
                'path: "{}", '
                'channel: "{}", '
                'deps: {}'
                '>').format(self.name, self.version, self._path, self._channel,
                            self._deps)


def parse_deps(env_name):
    all_deps = {}
    out_fd = subprocess.Popen(['conda', 'env', 'export', '-n', env_name],
                              universal_newlines=True,
                              stdout=subprocess.PIPE)
    pkgs = yaml.safe_load(out_fd.stdout)
    deps = pkgs['dependencies']
    channels = pkgs['channels']
    conda_meta_dpath = os.path.join(pkgs['prefix'], 'conda-meta')
    pip_deps = []
    if isinstance(deps[-1], dict) and 'pip' in deps[-1]:
        pip_deps = deps.pop()['pip']
    for dep in deps:
        name, ver = dep.split('=', 1)
        all_deps[name] = PackageSpec(name, ver)
    for dep in pip_deps:
        name, ver = dep.split('=', 1)
        all_deps[name] = PackageSpec(name, ver, from_pip=True)
    return all_deps, conda_meta_dpath, channels


def update_deps_with_conda_meta(env_name, conda_meta_dpath, all_deps):
    addl_deps = set()
    for root, dirnames, filenames in os.walk(conda_meta_dpath):
        for filename in filenames:
            if filename.endswith('.json'):
                with open(os.path.join(root, filename), 'r') as fp:
                    pkg_meta = yaml.safe_load(fp)
                pkg_name = pkg_meta['name']
                if pkg_name not in all_deps:
                    continue
                pkgspec = all_deps[pkg_name]
                pkgspec.path = pkg_meta['link']['source']
                pkgspec.channel = pkg_meta['schannel']
                pkgspec.deps = pkg_meta['depends']
                all_deps[pkg_name] = pkgspec
                addl_deps.update(pkgspec.deps.keys())
    return addl_deps


def render_deps_graph(all_deps, out_fname, ext):
    dg = gv.Digraph(filename=out_fname, format=ext)
    parent_map = defaultdict(int)
    for dep_name, dep_spec in all_deps.items():
        dg.node(dep_name)
        for depdep_name in dep_spec.deps:
            dg.edge(dep_name, depdep_name)
            parent_map[depdep_name] += 1
    dg.render()
    return parent_map


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('env_name', help='environment name')
    args = parser.parse_args(argv[1:])

    print('Loading dependencies from env "{}"...'.format(args.env_name),
          file=sys.stderr)
    all_deps, conda_meta_dpath, channels = parse_deps(args.env_name)

    print('Parsing conda metadata...', file=sys.stderr)
    update_deps_with_conda_meta(args.env_name, conda_meta_dpath, all_deps)

    out_fname = args.env_name + '_graph'
    ext = 'png'
    print('Generating dependency graph at "{}.{}"...'.format(out_fname, ext),
          file=sys.stderr)
    parent_map = render_deps_graph(all_deps, out_fname, ext)

    print('name: {}_minified'.format(args.env_name))
    print('channels:')
    for channel in channels:
        print('  - {}'.format(channel))
    print('dependencies:'.format(args.env_name))
    pip_deps = []
    for dep_name in all_deps:
        if dep_name not in parent_map:
            pkgspec = all_deps[dep_name]
            if pkgspec.from_pip:
                pip_deps.append(dep_name)
            else:
                print('  - {}={}'.format(dep_name, pkgspec.version))
    print('  - pip:')
    for dep_name in pip_deps:
        print('    - {}'.format(dep_name))


if __name__ == '__main__':
    sys.exit(main(sys.argv))
