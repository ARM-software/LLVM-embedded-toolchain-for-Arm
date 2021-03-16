#!/usr/bin/env python3

#
# Copyright (c) 2020, Arm Limited and affiliates.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import argparse
import os
import re
import textwrap
import sys

import git
import yaml

def die(msg, ret_val=1):
    """Exit from program with the specified message and return value."""
    print('Error: {}'.format(msg))
    sys.exit(ret_val)

def warn(msg):
    """Print a warning message."""
    print('Warning: {}'.format(msg))

class ModuleTC:
    """A building block of the LLVM Embedded Toolchain for Arm."""

    def __init__(self, module_yml):
        assert isinstance(module_yml, dict)
        for key in ['Name', 'URL', 'Revision']:
            assert key in module_yml, "ModuleTC is missing mandatory key '{}'".format(key)
        self.name = module_yml['Name']
        self.url = module_yml['URL']
        self.branch = module_yml['Branch'] if 'Branch' in module_yml else None
        self.revision = module_yml['Revision']
        self.patch = module_yml['Patch'] if 'Patch' in module_yml else None
        if self.revision == 'HEAD'and self.branch is None:
            die('for repository {}, HEAD needs a branch name !'.format(self.name))

    def __repr__(self):
        return ', '.join(self.yamlize())

    def yamlize(self):
        """Convert to YAML represented as a list of lines."""
        res = list()
        res.append('Name: {}'.format(self.name))
        res.append('URL: {}'.format(self.url))
        if self.branch:
            res.append('Branch: {}'.format(self.branch))
        res.append('Revision: {}'.format(self.revision))
        return res

class LLVMBMTC:
    """An LLVM Embedded Toolchain for Arm package."""

    def __init__(self, data_yml):
        assert isinstance(data_yml, dict), 'Toolchains must be a dict !'
        assert 'Revision' in data_yml, 'Toolchain is missing a revision !'
        assert 'Modules' in data_yml, 'Toolchain is missing a modules list !'
        assert isinstance(data_yml['Modules'], list), 'Toolchains modules must be a list !'
        self.revision = str(data_yml['Revision'])
        self.modules = {}
        for module_yml in data_yml['Modules']:
            module = ModuleTC(module_yml)
            if module.name in self.modules:
                die('repository {} already exists !'.format(module.name))
            self.modules[module.name] = module

    def __repr__(self):
        modules = ', '.join(map(repr, list(self.modules.values())))
        return '{}(revision:"{}", modules:[{}])'.format(self.__class__.__name__,
                self.revision, modules)

def get_all_versions(filename):
    """ Build the database containing all releases from a YAML file."""
    assert isinstance(filename, str), "Expecting a string for the file name."
    versions = dict()
    with open(filename, 'r') as stream:
        try:
            yml = yaml.load(stream, Loader=yaml.FullLoader)
            for value in yml:
                toolchain = LLVMBMTC(value)
                if toolchain.revision in versions:
                    die('toolchain revision {} previously defined !'.format(toolchain.revision))
                versions[toolchain.revision] = toolchain
        except yaml.YAMLError as exc:
            print(exc)

    return versions

def print_versions(versions, verbose):
    """Print releases (as parsed from a YAML file)"""
    assert isinstance(versions, dict), "Expecting a dictionary of versions."
    if verbose:
        for version, toolchain in list(versions.items()):
            print(' - revision: {}'.format(version))
            print('   modules:')
            for module in list(toolchain.modules.values()):
                print('    - {}'.format(module))
    else:
        print("\n".join(versions.keys()))

    return 0

def find_all_git_repositories(repositories):
    """ Walk repositories to find all GIT checkouts."""
    assert isinstance(repositories, str), "Expecting a string for the directory name."
    if not os.path.isdir(repositories):
        die("repositories location '{}' does not exists !".format(repositories))
    repos = list()
    for root, sub_dirs, _ in os.walk(repositories):
        if '.git' in sub_dirs:
            repos.append(root)
    return repos

def get_repositories_status(repositories):
    """ Get the state of each git repository."""
    assert isinstance(repositories, str), "Expecting a string for the directory name."
    status = dict()
    repos = find_all_git_repositories(repositories)
    rex = re.compile('^' + repositories + r'\/')
    for repo_path in repos:
        repo = git.Repo(repo_path)
        rel_path = rex.sub('', repo_path)
        status[rel_path] = {
                       'SHA1': repo.head.commit.hexsha,
                       'Dirty': repo.is_dirty(),
                       'URL': repo.git.config('--get', 'remote.origin.url')
                     }
        if repo.head.is_detached:
            status[rel_path]['Branch'] = None
        else:
            status[rel_path]['Branch'] = repo.active_branch.name
    return status

def print_repositories_status(repositories):
    """ Report the state of each git repository."""
    assert isinstance(repositories, str), "Expecting a string for the directory name."
    statuses = get_repositories_status(repositories)
    print("Status (in directory '{}'):".format(repositories))
    for repo, status in list(statuses.items()):
        if status['Branch'] is None:
            print(" - {}: Detached, Revision:{}, Dirty:{}".format(repo,
                    status['SHA1'], status['Dirty']))
        else:
            print(" - {}: Branch:{}, Revision:{}, Dirty:{}".format(repo, status['Branch'],
                    status['SHA1'], status['Dirty']))

    return 0

def check_repositories_status(repositories, tc_version):
    """ Check the state of each git repository against the one stored in the release database."""
    assert isinstance(repositories, str), "Expecting a string for the directory name."
    assert isinstance(tc_version, LLVMBMTC), "Expecting an LLVMBMTC object."
    statuses = get_repositories_status(repositories)
    ret_val = 0
    print("Check (in directory '{}', for revision '{}'):".format(repositories, tc_version.revision))
    if len(statuses) != len(tc_version.modules):
        warn('{} and {} do not have the same number of modules !'.format(repositories, tc_version.revision))
        ret_val = 1

    for repo, status in list(statuses.items()):
        msg = []
        if repo not in tc_version.modules:
            die('{} was not found in the revision database !'.format(repo))
        module = tc_version.modules[repo]
        if status['Dirty']:
            msg.append('Dirty')
        if status['Branch'] != module.branch:
            msg.append('Branch mismatch ({}, {})'.format(status['Branch'], module.branch))
        if module.revision != 'HEAD' and status['SHA1'] != module.revision:
            msg.append('Commit mismatch ({}, {})'.format(status['SHA1'], module.revision))
        if len(msg) == 0:
            msg.append('OK')
        else:
            ret_val = 1
        print(" - {}: {}".format(repo, ', '.join(msg)))

    return ret_val

def clone_repositories(repositories, tc_version, patches):
    """ Checkout each git repository for tc_version in directory repositories."""
    assert isinstance(repositories, str), "Expecting a string for the directory name."
    assert isinstance(tc_version, LLVMBMTC), "Expecting an LLVMBMTC object."
    if os.path.isdir(repositories):
        # Ensure the directory is empty if it exists
        if os.listdir(repositories):
            die("repositories location '{}' is not empty !".format(repositories))
    else:
        os.mkdir(repositories)

    repos = list(tc_version.modules.keys())

    print('Clone ({} @ {}):'.format(repositories, tc_version.revision))
    for repo_path in repos:
        module = tc_version.modules[repo_path]
        print(' - {}: {} @ {}{}'.format(repo_path, module.branch, module.revision,
                                 ' (detached)' if module.revision != 'HEAD' else ''))
        repo = git.Repo.clone_from(module.url, os.path.join(repositories, module.name))
        if module.revision == 'HEAD':
            try:
                repo.git.checkout(module.branch)
            except git.exc.GitCommandError as ex: # pylint: disable=no-member
                die("could not checkout '{}' @ '{}/{}' !\nGit command failed with:\n{}".format(repo_path, module.branch, module.revision, ex))
        else:
            # Detached state
            try:
                repo.git.checkout(module.revision)
            except git.exc.GitCommandError as ex: # pylint: disable=no-member
                die("could not checkout '{}' @ '{}' !\nGit command failed with:\n{}".format(repo_path, module.revision, ex))

        if module.patch:
            patch_file = os.path.join(patches, module.patch)
            if not os.path.isfile(patch_file):
                die("patch file '{}' not found !".format(patch_file))

            print(' - {}: patch {}'.format(repo_path, patch_file))
            try:
                repo.git.apply(['-p1', patch_file])
            except git.exc.GitCommandError as ex: # pylint: disable=no-member
                die("could not patch '{}' with '{}' !\nGit command failed with:\n{}".format(repo_path, patch_file, ex))

    return 0

def freeze_repositories(repositories, version):
    """ Print a YAML compatible output of the repositories state."""
    assert isinstance(repositories, str), "Expecting a string for the directory name."
    assert isinstance(version, str), "Expecting a string for the version."
    statuses = get_repositories_status(repositories)
    for repo, status in list(statuses.items()):
        if status['Dirty']:
            die("'{}' is in a dirty state. Refusing to freeze !".format(repo))
    print('- Revision: {}'.format(version))
    print('  Modules:')
    for repo, status in list(statuses.items()):
        print('    - Name: {}'.format(repo))
        print('      URL: {}'.format(status['URL']))
        print('      Revision: {}'.format(status['SHA1']))

    return 0

def main():
    parser = argparse.ArgumentParser(
            description='Manage LLVM Embedded Toolchain for Arm checkout',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=textwrap.dedent('''\

            Actions:
              list     list available versions.
              status   report the status of each checkout.
              check    check the state of each checkout matches the requested toolchain revision
              clone    checkout each repository as needed for the requested toolchian revision
              freeze   print a YAML description of the current repositories state

            '''))
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Increase verbosity level.')
    parser.add_argument('-r', '--revision', metavar='version', default='HEAD',
                        help='Select the toolchain version to use.')
    parser.add_argument('--patches', metavar='DIR', default='patches',
                        help='Select where the patch files are checked out.')
    parser.add_argument('--repositories', metavar='DIR', default='repos',
                        help='Select where the modules are checked out.')
    parser.add_argument('--versions', metavar='FILE', default='versions.yml',
                        help='Select the database of available toolchain reversions.')
    parser.add_argument('action', nargs=1,
                        choices=['list', 'status', 'check', 'clone', 'freeze'],
                        help='Action to perform')

    args = parser.parse_args()
    args.action = args.action[0]

    ret_val = 0
    if args.action == 'status':
        ret_val = print_repositories_status(args.repositories)
        sys.exit(ret_val)
    elif args.action == 'freeze':
        ret_val = freeze_repositories(args.repositories, args.revision)
        sys.exit(ret_val)

    versions = get_all_versions(args.versions)

    # Make sure the requested version actually exists
    if args.revision not in versions:
        die("revision '{}' is unknown !".format(args.revision))

    if args.action == 'list':
        ret_val = print_versions(versions, args.verbose)
    elif args.action == 'check':
        ret_val = check_repositories_status(args.repositories, versions[args.revision])
    elif args.action == 'clone':
        ret_val = clone_repositories(args.repositories, versions[args.revision], args.patches)
    else:
        die("Error ! Unsupported command '{}' !".format(args.action))

    sys.exit(ret_val)

if __name__ == '__main__':
    main()
