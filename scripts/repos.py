#!/usr/bin/env python3

#
# Copyright (c) 2020-2021, Arm Limited and affiliates.
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
import textwrap
import sys
from typing import Dict, List, Any

import git
import yaml


def die(msg: str, ret_val=1) -> None:
    """Exit from program with the specified message and return value."""
    print('Error: {}'.format(msg))
    sys.exit(ret_val)


def warn(msg: str) -> None:
    """Print a warning message."""
    print('Warning: {}'.format(msg))


class ModuleTC:
    """A building block of the LLVM Embedded Toolchain for Arm."""
    def __init__(self, module_yml: Dict[str, str]):
        for key in ['Name', 'URL', 'Revision']:
            assert key in module_yml, (
                'ModuleTC is missing mandatory key "{}"'.format(key))
        self.name = module_yml['Name']
        self.url = module_yml['URL']
        self.branch = module_yml['Branch'] if 'Branch' in module_yml else None
        self.revision = module_yml['Revision']
        self.patch = module_yml['Patch'] if 'Patch' in module_yml else None
        if self.revision == 'HEAD' and self.branch is None:
            die('for repository {}, HEAD needs a branch name'.format(
                self.name))

    def __repr__(self):
        return ', '.join(self.yamlize())

    def yamlize(self) -> List[str]:
        """Convert to YAML represented as a list of lines."""
        res = [
            'Name: {}'.format(self.name),
            'URL: {}'.format(self.url),
        ]
        if self.branch:
            res.append('Branch: {}'.format(self.branch))
        res.append('Revision: {}'.format(self.revision))
        return res


class LLVMBMTC:
    """An LLVM Embedded Toolchain for Arm package."""
    def __init__(self, data_yml: Dict[str, Any]):
        assert 'Revision' in data_yml, 'Toolchain is missing a revision'
        assert 'Modules' in data_yml, 'Toolchain is missing a modules list'
        assert isinstance(data_yml['Modules'], list), (
            'Toolchains modules must be a list')
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


def get_all_versions(filename: str) -> Dict[str, Any]:
    """Build the database containing all releases from a YAML file."""
    versions = {}
    with open(filename, 'r') as stream:
        try:
            yml = yaml.load(stream, Loader=yaml.FullLoader)
            for value in yml:
                toolchain = LLVMBMTC(value)
                if toolchain.revision in versions:
                    die('toolchain revision {} previously defined'.format(
                        toolchain.revision))
                versions[toolchain.revision] = toolchain
        except yaml.YAMLError as ex:
            print(ex)

    return versions


def print_versions(versions: Dict[str, Any], verbose: bool) -> int:
    """Print releases (as parsed from a YAML file)."""
    if verbose:
        for version, toolchain in versions.items():
            print(' - revision: {}'.format(version))
            print('   modules:')
            for module in list(toolchain.modules.values()):
                print('    - {}'.format(module))
    else:
        print('\n'.join(versions.keys()))

    return 0


def find_all_git_repositories(checkout_path: str) -> List[str]:
    """Walk repositories to find all GIT checkouts."""
    if not os.path.isdir(checkout_path):
        die("repositories location '{}' does not exists!".format(
            checkout_path))
    repos = []
    for root, sub_dirs, _ in os.walk(checkout_path):
        if '.git' in sub_dirs:
            repos.append(root)
    return repos


def get_repositories_status(checkout_path: str) -> Dict[str, Any]:
    """Get the state of each git repository."""
    status = {}
    repos = find_all_git_repositories(checkout_path)
    for repo_path in repos:
        repo = git.Repo(repo_path)
        rel_path = os.path.relpath(repo_path, checkout_path)
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


def print_repositories_status(checkout_path: str) -> int:
    """Report the state of each git repository."""
    statuses = get_repositories_status(checkout_path)
    print('Status (in directory "{}"):'.format(checkout_path))
    for repo, status in statuses.items():
        if status['Branch'] is not None:
            branch_str = 'Branch: {}'.format(status['Branch'])
        else:
            branch_str = 'Detached'
        print(' - {}: {}, Revision: {}, Dirty: {}'.format(
              repo, branch_str, status['SHA1'], status['Dirty']))

    return 0


def check_repositories_status(checkout_path: str, tc_version: LLVMBMTC) -> int:
    """Check the state of each git repository against the one stored in the
       release database.
    """
    statuses = get_repositories_status(checkout_path)
    ret_val = 0
    print('Check (in directory "{}", for revision "{}"):'.format(
        checkout_path, tc_version.revision))
    if len(statuses) != len(tc_version.modules):
        warn('{} and {} do not have the same number of modules'.format(
            checkout_path, tc_version.revision))
        ret_val = 1

    for repo, status in statuses.items():
        msg = []
        if repo not in tc_version.modules:
            die('{} was not found in the revision database'.format(repo))
        module = tc_version.modules[repo]
        if status['Dirty']:
            msg.append('Dirty')
        if status['Branch'] != module.branch:
            msg.append('Branch mismatch ({}, {})'.format(
                status['Branch'], module.branch))
        if module.revision != 'HEAD' and status['SHA1'] != module.revision:
            msg.append('Commit mismatch ({}, {})'.format(
                status['SHA1'], module.revision))
        if len(msg) == 0:
            msg.append('OK')
        else:
            ret_val = 1
        print(' - {}: {}'.format(repo, ', '.join(msg)))

    return ret_val


def patch_repositories(checkout_path: str, tc_version: LLVMBMTC,
                       patches: str) -> int:
    """Reset checked out repositories and apply patches."""
    for repo_name, module in tc_version.modules.items():
        if not module.patch:
            continue
        repo_path = os.path.join(checkout_path, repo_name)
        patch_file = os.path.join(patches, module.patch)
        if not os.path.isfile(patch_file):
            die('patch file "{}" not found'.format(patch_file))

        print(' - {}: patch {}'.format(repo_path, patch_file))
        repo = git.Repo(repo_path)
        try:
            repo.head.reset(index=True, working_tree=True)
            repo.git.apply(['-p1', patch_file])
        except git.exc.GitCommandError as ex: # pylint: disable=no-member
            die('could not patch "{}" with "{}".\n'
                'Git command failed with:\n{}'
                .format(repo_path, patch_file, ex))
    return 0


def clone_repositories(checkout_path: str, tc_version: LLVMBMTC,
                       patches: str) -> int:
    """Checkout each git repository for tc_version in the directory
       checkout_path.
    """
    if os.path.isdir(checkout_path):
        # Ensure the directory is empty if it exists
        if os.listdir(checkout_path):
            die('repositories location "{}" is not empty'.format(
                checkout_path))
    else:
        os.mkdir(checkout_path)

    print('Clone ({} @ {}):'.format(checkout_path, tc_version.revision))
    for repo_path, module in tc_version.modules.items():
        print(' - {}: {} @ {}{}'.format(
            repo_path, module.branch, module.revision,
            ' (detached)' if module.revision != 'HEAD' else ''))
        repo = git.Repo.clone_from(module.url,
                                   os.path.join(checkout_path, module.name))
        if module.revision == 'HEAD':
            try:
                repo.git.checkout(module.branch)
            except git.exc.GitCommandError as ex: # pylint: disable=no-member
                die('could not checkout "{}" @ "{}/{}"\n'
                    'Git command failed with:\n{}'
                    .format(repo_path, module.branch, module.revision, ex))
        else:
            # Detached state
            try:
                repo.git.checkout(module.revision)
            except git.exc.GitCommandError as ex: # pylint: disable=no-member
                die('could not checkout "{}" @ "{}".\n'
                    'Git command failed with:\n{}'
                    .format(repo_path, module.revision, ex))

    return patch_repositories(checkout_path, tc_version, patches)


def freeze_repositories(checkout_path: str, version: str) -> int:
    """Print a YAML compatible output of the repositories state."""
    statuses = get_repositories_status(checkout_path)
    for repo, status in statuses.items():
        if status['Dirty']:
            die('"{}" is in a dirty state. Refusing to freeze.'.format(repo))
    print('- Revision: {}'.format(version))
    print('  Modules:')
    for repo, status in statuses.items():
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
    parser.add_argument('-v',
                        '--verbose',
                        action='store_true',
                        help='Increase verbosity level.')
    parser.add_argument('-r',
                        '--revision',
                        metavar='version',
                        default='HEAD',
                        help='Select the toolchain version to use.')
    parser.add_argument('--patches',
                        metavar='DIR',
                        default='patches',
                        help='Select where the patch files are checked out.')
    parser.add_argument('--repositories',
                        metavar='DIR',
                        default='repos',
                        help='Select where the modules are checked out.')
    parser.add_argument(
        '--versions',
        metavar='FILE',
        default='versions.yml',
        help='Select the database of available toolchain reversions.')
    parser.add_argument('action',
                        nargs=1,
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
        die('revision "{}" is unknown'.format(args.revision))

    if args.action == 'list':
        ret_val = print_versions(versions, args.verbose)
    elif args.action == 'check':
        ret_val = check_repositories_status(args.repositories,
                                            versions[args.revision])
    elif args.action == 'clone':
        ret_val = clone_repositories(args.repositories, versions[args.revision],
                                     args.patches)
    else:
        die('unsupported command: "{}"'.format(args.action))

    sys.exit(ret_val)


if __name__ == '__main__':
    main()
