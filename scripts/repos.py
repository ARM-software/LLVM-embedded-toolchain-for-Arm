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
import logging
import os
import re
import shutil
import sys
from typing import List, Mapping, Optional, Any

import git  # type: ignore

import util


def die(msg: str, ret_val=1) -> None:
    """Exit from program with the specified message and return value."""
    logging.error(msg)
    sys.exit(ret_val)


class RepositoryStatus:
    """Status of a checked out git repository"""
    def __init__(self, repo_path):
        repo = git.Repo(repo_path)
        self.sha1 = repo.head.commit.hexsha
        self.is_dirty = repo.is_dirty()
        self.url = repo.git.config('--get', 'remote.origin.url')
        self.branch = None
        if not repo.head.is_detached:
            self.branch = repo.active_branch.name

    def __repr__(self):
        branch_str = ('Branch: {}'.format(self.branch)
                      if self.branch is not None else 'Detached')
        return '{}, Revision: {}, Dirty: {}'.format(branch_str,
                                                    self.sha1,
                                                    self.is_dirty)


class ModuleTC:
    """A building block of the LLVM Embedded Toolchain for Arm."""
    def __init__(self, module_yml: Mapping[str, str]):
        for key in ['Name', 'FriendlyName', 'URL', 'Revision']:
            assert key in module_yml, (
                'ModuleTC is missing mandatory key "{}"'.format(key))
        self.name = module_yml['Name']
        self.friendly_name = module_yml['FriendlyName']
        self.url = module_yml['URL']
        self.branch = module_yml['Branch'] if 'Branch' in module_yml else None
        self.revision = module_yml['Revision']
        self.patch = module_yml['Patch'] if 'Patch' in module_yml else None
        self.status: Optional[RepositoryStatus] = None
        if self.revision == 'HEAD' and self.branch is None:
            die('for repository {}, HEAD needs a branch name'.format(
                self.name))

    def __repr__(self):
        return ', '.join(self.yamlize())

    @property
    def checkout_info(self):
        """Returns description of a checked out commit of the module."""
        commit = (self.status.sha1 if self.status is not None else
                  '<unknown commit>')
        tag_or_branch = ('Tip of the branch {}'.format(self.branch)
                         if self.revision == 'HEAD' else self.revision)
        return '{}: {}, {} (commit {})'.format(self.friendly_name,
                                               self.url,
                                               tag_or_branch,
                                               commit)

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


def get_repositories_status(checkout_path: str) -> \
        Mapping[str, RepositoryStatus]:
    """Get the state of each git repository."""
    status = {}
    repos = find_all_git_repositories(checkout_path)
    for repo_path in repos:
        rel_path = os.path.relpath(repo_path, checkout_path)
        status[rel_path] = RepositoryStatus(repo_path)
    return status


class LLVMBMTC:
    """An LLVM Embedded Toolchain for Arm package."""
    def __init__(self, data_yml: Mapping[str, Any]):
        assert 'Revision' in data_yml, 'Toolchain is missing a revision'
        assert 'Modules' in data_yml, 'Toolchain is missing a modules list'
        assert isinstance(data_yml['Modules'], list), (
            'Toolchains modules must be a list')
        self.revision = str(data_yml['Revision'])
        self.modules: Mapping[str, ModuleTC] = {}
        for module_yml in data_yml['Modules']:
            module = ModuleTC(module_yml)
            if module.name in self.modules:
                die('repository {} already exists !'.format(module.name))
            self.modules[module.name] = module

    def __repr__(self):
        modules = ', '.join(map(repr, list(self.modules.values())))
        return '{} (revision:"{}", modules:[{}])'.format(
            self.__class__.__name__, self.revision, modules)

    def poplulate_commits(self, repos_dir: str) -> None:
        """Populate commit hashes from checked out repositoties."""
        # Check if commit hashes have already been set
        if all(module.status is not None for module in self.modules.values()):
            return
        status = get_repositories_status(repos_dir)
        for name, module in self.modules.items():
            if name not in status:
                logging.warning('Could not get status for %s', name)
                continue
            module.status = status[name]


def get_all_versions(filename: str) -> Mapping[str, LLVMBMTC]:
    """Build the database containing all releases from a YAML file."""
    versions = {}
    yml = util.read_yaml(filename)
    for value in yml['Revisions']:
        toolchain = LLVMBMTC(value)
        if toolchain.revision in versions:
            die('toolchain revision {} previously defined'.format(
                toolchain.revision))
        versions[toolchain.revision] = toolchain

    return versions


def print_versions(versions: Mapping[str, LLVMBMTC], verbose: bool) -> None:
    """Print releases (as parsed from a YAML file)."""
    if verbose:
        for version, toolchain in versions.items():
            print(' - revision: {}'.format(version))
            print('   modules:')
            for module in list(toolchain.modules.values()):
                print('    - {}'.format(module))
    else:
        print('\n'.join(versions.keys()))


def print_repositories_status(checkout_path: str) -> None:
    """Report the state of each git repository."""
    statuses = get_repositories_status(checkout_path)
    print('Status (in directory "{}"):'.format(checkout_path))
    for repo, status in statuses.items():
        print(' - {}: {}'.format(repo, status))


def check_repositories_status(checkout_path: str, tc_version: LLVMBMTC) -> int:
    """Check the state of each git repository against the one stored in the
       release database.
    """
    statuses = get_repositories_status(checkout_path)
    ret_val = 0
    logging.info('Check (in directory "%s", for revision "%s"):',
                 checkout_path, tc_version.revision)
    if len(statuses) != len(tc_version.modules):
        logging.warning('%s and %s do not have the same number of modules',
                        checkout_path, tc_version.revision)
        ret_val = 1

    for repo, status in statuses.items():
        msg = []
        if repo not in tc_version.modules:
            die('{} was not found in the revision database'.format(repo))
        module = tc_version.modules[repo]
        if status.is_dirty:
            msg.append('Dirty')
        if status.branch != module.branch:
            msg.append('Branch mismatch ({}, {})'.format(status.branch,
                                                         module.branch))
        if module.revision != 'HEAD' and status.sha1 != module.revision:
            msg.append('Commit mismatch ({}, {})'.format(status.sha1,
                                                         module.revision))
        if len(msg) == 0:
            msg.append('OK')
        else:
            ret_val = 1
        logging.info(' - %s: %s', repo, ', '.join(msg))

    return ret_val


def patch_repositories(checkout_path: str, tc_version: LLVMBMTC,
                       patches: str) -> None:
    """Reset checked out repositories and apply patches."""
    for repo_name, module in tc_version.modules.items():
        if not module.patch:
            continue
        repo_path = os.path.join(checkout_path, repo_name)
        patch_file = os.path.join(patches, module.patch)
        if not os.path.isfile(patch_file):
            die('patch file "{}" not found'.format(patch_file))

        logging.info(' - %s: patch %s', repo_path, patch_file)
        repo = git.Repo(repo_path)
        try:
            repo.head.reset(index=True, working_tree=True)
            # Remove ignored files (our newlib patch contains one)
            repo.git.clean(['-fX'])
            repo.git.apply(['-p1', patch_file])
        except git.exc.GitCommandError as ex:  # pylint: disable=no-member
            die('could not patch "{}" with "{}".\n'
                'Git command failed with:\n{}'
                .format(repo_path, patch_file, ex))


def is_hash_like(refspec: str) -> bool:
    """Return true if refspec looks like a commit hash rather than a
       branch/tag. Does not work for abbreviated hashes."""
    return re.match('[0-9a-f]{20}', refspec) is not None


def clone_repositories(checkout_path: str, tc_version: LLVMBMTC,
                       patches: str) -> None:
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

    logging.info('Clone (%s @ %s):', checkout_path, tc_version.revision)
    for repo_path, module in tc_version.modules.items():
        logging.info(' - %s: %s @ %s%s', repo_path,
                     module.branch if module.branch else '(no branch)',
                     module.revision,
                     ' (detached)' if module.revision != 'HEAD' else '')
        refspec = (module.branch if module.revision == 'HEAD'
                   else module.revision)
        assert refspec is not None

        if is_hash_like(refspec):
            # Git cannot perfom a shallow clone from a commit hash. Run full
            # clone and then checkout.
            repo = git.Repo.clone_from(module.url,
                                       os.path.join(checkout_path,
                                                    module.name))
            repo.git.checkout(module.revision)
        else:
            # If refspec is a branch or a tag, use shallow clone
            repo = git.Repo.clone_from(module.url,
                                       os.path.join(checkout_path,
                                                    module.name),
                                       multi_options=[
                                           "--branch %s" % (refspec),
                                           "--depth 1"
                                       ])

    patch_repositories(checkout_path, tc_version, patches)


def export_repository(src_repo_path: str, dest_repo_path: str,
                      copy_untracked: bool = False) -> None:
    """Copy the files of a checked out repository to a new directory. The copy
       will include unstaged changes and optionally untracked files if
       copy_untracked is True."""
    logging.info('Exporting "%s" to "%s"', src_repo_path, dest_repo_path)
    git_cmd = git.cmd.Git(src_repo_path)
    args = ['--cached']
    if copy_untracked:
        args.append('--other')
    for fname in git_cmd.ls_files(*args).splitlines():
        src_path = os.path.join(src_repo_path, fname)
        dest_path = os.path.join(dest_repo_path, fname)
        dest_dir = os.path.dirname(dest_path)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        shutil.copy2(src_path, dest_path, follow_symlinks=False)


def export_toolchain_repositories(checkout_path: str, tc_version: LLVMBMTC,
                                  dest_path: str) -> None:
    """Export all checked out repositories."""
    for repo_dir in tc_version.modules.keys():
        export_repository(os.path.join(checkout_path, repo_dir),
                          os.path.join(dest_path, repo_dir),
                          True)


def freeze_repositories(checkout_path: str, version: str) -> None:
    """Print a YAML compatible output of the repositories state."""
    statuses = get_repositories_status(checkout_path)
    for repo, status in statuses.items():
        if status.is_dirty:
            die('"{}" is in a dirty state. Refusing to freeze.'.format(repo))
    print('- Revision: {}'.format(version))
    print('  Modules:')
    for repo, status in statuses.items():
        print('    - Name: {}'.format(repo))
        print('      URL: {}'.format(status.url))
        print('      Revision: {}'.format(status.sha1))


def main():
    util.configure_logging()

    parser = argparse.ArgumentParser(
        description='Manage LLVM Embedded Toolchain for Arm checkout',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='\n'
               'Actions:\n'
               '  list     list available versions.\n'
               '  status   report the status of each checkout.\n'
               '  check    check the state of each checkout matches the '
               'requested toolchain revision\n'
               '  clone    checkout each repository as needed for the '
               'requested toolchain revision\n'
               '  freeze   print a YAML description of the current '
               'repositories state\n')
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

    if args.action == 'status':
        print_repositories_status(args.repositories)
        sys.exit(0)
    elif args.action == 'freeze':
        freeze_repositories(args.repositories, args.revision)
        sys.exit(0)

    ret_val = 0
    versions = get_all_versions(args.versions)

    # Make sure the requested version actually exists
    if args.revision not in versions:
        die('revision "{}" is unknown'.format(args.revision))

    if args.action == 'list':
        print_versions(versions, args.verbose)
    elif args.action == 'check':
        ret_val = check_repositories_status(args.repositories,
                                            versions[args.revision])
    elif args.action == 'clone':
        clone_repositories(args.repositories, versions[args.revision],
                           args.patches)
    else:
        die('unsupported command: "{}"'.format(args.action))

    sys.exit(ret_val)


if __name__ == '__main__':
    main()
