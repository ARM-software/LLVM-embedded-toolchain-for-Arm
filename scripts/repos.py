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
import yaml
import os
import re
import git
import textwrap
import sys

def die(msg, rv=1):
    """Exit from program with the specified message and return value."""
    print('Error: {}'.format(msg))
    sys.exit(rv)

def warn(msg):
    """Print a warning message."""
    print('Warning: {}'.format(msg))

class ModuleTC(object):
    """A building block of the LLVM Embedded Toolchain for Arm."""

    def __init__(self, d):
        assert isinstance(d, dict)
        for k in ['Name', 'URL', 'Revision']:
            assert k in d, "ModuleTC is missing mandatory key '{}'".format(k)
        self.Name = d['Name']
        self.URL = d['URL']
        self.Branch = d['Branch'] if 'Branch' in d else None
        self.Revision = d['Revision']
        self.Patch = d['Patch'] if 'Patch' in d else None
        if self.Revision == 'HEAD'and self.Branch is None:
            die('for repository {}, HEAD needs a branch name !'.format(self.Name))

    def __repr__(self):
        return ', '.join(self.yamlize())

    def yamlize(self):
        l = list()
        l.append('Name: {}'.format(self.Name))
        l.append('URL: {}'.format(self.URL))
        if self.Branch:
            l.append('Branch: {}'.format(self.Branch))
        l.append('Revision: {}'.format(self.Revision))
        return l

class LLVMBMTC(object):
    """An LLVM Embedded Toolchain for Arm package."""

    def __init__(self, d):
        assert isinstance(d, dict), 'Toolchains must be a dict !'
        assert 'Revision' in d, 'Toolchain is missing a revision !'
        assert 'Modules' in d, 'Toolchain is missing a modules list !'
        assert isinstance(d['Modules'], list), 'Toolchains Modules must be a list !'
        self.Revision = str(d['Revision'])
        self.Modules = dict()
        for M in d['Modules']:
            theModule = ModuleTC(M)
            if theModule.Name in self.Modules:
                die('repository {} already exists !'.format(theModule.Name))
            self.Modules[theModule.Name] = theModule

    def __repr__(self):
        modules = ', '.join(map(repr, list(self.Modules.values())))
        return '{}(Revision:"{}", Modules:[{}])'.format(self.__class__.__name__,
                self.Revision, modules)

def getAllVersions(filename):
    """ Build the database containing all releases from a YAML file."""
    assert isinstance(filename, str), "Expecting a string for the file name."
    versions = dict()
    with open(filename, 'r') as stream:
        try:
            yml = yaml.load(stream, Loader=yaml.FullLoader)
            for v in yml:
                TC = LLVMBMTC(v)
                if TC.Revision in versions:
                    die('toolchain revision {} previously defined !'.format(TC.Revision))
                versions[TC.Revision] = TC
        except yaml.YAMLError as exc:
            print(exc)

    return versions

def printVersions(versions, verbose):
    assert isinstance(versions, dict), "Expecting a dictionary of versions."
    if verbose:
        for v, tc in list(versions.items()):
            print(' - Revision: {}'.format(v))
            print('   Modules:')
            for M in list(tc.Modules.values()):
                print('    - {}'.format(M))
    else:
        print("\n".join(versions.keys()))

    return 0

def findAllGitRepositories(repositories):
    """ Walk repositories to find all GIT checkouts."""
    assert isinstance(repositories, str), "Expecting a string for the directory name."
    if not os.path.isdir(repositories):
        die("repositories location '{}' does not exists !".format(repositories))
    repos = list()
    for root, subFolders, files in os.walk(repositories):
        if '.git' in subFolders:
            repos.append(root)
    return repos

def getRepositoriesStatus(repositories):
    """ Get the state of each git repository."""
    assert isinstance(repositories, str), "Expecting a string for the directory name."
    status = dict()
    repos = findAllGitRepositories(repositories)
    p = re.compile('^' + repositories + '\/')
    for R in repos:
        repo = git.Repo(R)
        Rp = p.sub('', R)
        status[Rp] = {
                       'SHA1': repo.head.commit.hexsha,
                       'Dirty': repo.is_dirty(),
                       'URL': repo.git.config('--get', 'remote.origin.url')
                     }
        if repo.head.is_detached:
            status[Rp]['Branch'] = None
        else:
            status[Rp]['Branch'] = repo.active_branch.name
    return status

def printRepositoriesStatus(repositories):
    """ Report the state of each git repository."""
    assert isinstance(repositories, str), "Expecting a string for the directory name."
    status = getRepositoriesStatus(repositories)
    print("Status (in directory '{}'):".format(repositories))
    for R, S in list(status.items()):
        if S['Branch'] is None:
            print(" - {}: Detached, Revision:{}, Dirty:{}".format(R,
                    S['SHA1'], S['Dirty']))
        else:
            print(" - {}: Branch:{}, Revision:{}, Dirty:{}".format(R, S['Branch'],
                    S['SHA1'], S['Dirty']))

    return 0

def checkRepositoriesStatus(repositories, TCVersion):
    """ Check the state of each git repository against the one stored in the release database."""
    assert isinstance(repositories, str), "Expecting a string for the directory name."
    assert isinstance(TCVersion, LLVMBMTC), "Expecting an LLVMBMTC object."
    status = getRepositoriesStatus(repositories)
    rv = 0
    print("Check (in directory '{}', for revision '{}'):".format(repositories, TCVersion.Revision))
    if len(status) != len(TCVersion.Modules):
        warn('{} and {} do not have the same number of modules !'.format(repositories, TCVersion.Revision))
        rv = 1

    for R, S in list(status.items()):
        msg = list()
        if R not in TCVersion.Modules:
            die('{} was not found in the revision database !'.format(R))
        M = TCVersion.Modules[R]
        if S['Dirty']:
            msg.append('Dirty')
        if S['Branch'] != M.Branch:
            msg.append('Branch mismatch ({}, {})'.format(S['Branch'], M.Branch))
        if M.Revision != 'HEAD' and S['SHA1'] != M.Revision:
            msg.append('Commit mismatch ({}, {})'.format(S['SHA1'], M.Revision))
        if len(msg) == 0:
            msg.append('OK')
        else:
            rv = 1
        print(" - {}: {}".format(R, ', '.join(msg)))

    return rv

def cloneRepositories(repositories, TCVersion, patches):
    """ Checkout each git repository for TCVersion in directory repositories."""
    assert isinstance(repositories, str), "Expecting a string for the directory name."
    assert isinstance(TCVersion, LLVMBMTC), "Expecting an LLVMBMTC object."
    if os.path.isdir(repositories):
        # Ensure the directory is empty if it exists
        if os.listdir(repositories):
            die("repositories location '{}' is not empty !".format(repositories))
    else:
        os.mkdir(repositories)

    repos = list(TCVersion.Modules.keys())

    print('Clone ({} @ {}):'.format(repositories, TCVersion.Revision))
    for R in repos:
        M = TCVersion.Modules[R]
        print(' - {}: {} @ {}{}'.format(R, M.Branch, M.Revision,
                                 ' (detached)' if M.Revision != 'HEAD' else ''))
        repo = git.Repo.clone_from(M.URL, os.path.join(repositories, M.Name))
        if M.Revision == 'HEAD':
            try:
                repo.git.checkout(M.Branch)
            except git.exc.GitCommandError as exc:
                die("could not checkout '{}' @ '{}/{}' !\nGit command failed with:\n{}".format(R, M.Branch, M.Revision, exc))
        else:
            # Detached state
            try:
                repo.git.checkout(M.Revision)
            except git.exc.GitCommandError as exc:
                die("could not checkout '{}' @ '{}' !\nGit command failed with:\n{}".format(R, M.Revision, exc))

        if M.Patch:
            patchFile = os.path.join(patches, M.Patch)
            if not os.path.isfile(patchFile):
                die("patch file '{}' not found !".format(patchFile))

            print(' - {}: patch {}'.format(R, patchFile))
            try:
                repo.git.apply(['-p1', patchFile])
            except git.exc.GitCommandError as exc:
                die("could not patch '{}' with '{}' !\nGit command failed with:\n{}".format(R, patchFile, exc))

    return 0

def freezeRepositories(repositories, version):
    """ Print a YAML compatible output of the repositories state."""
    assert isinstance(repositories, str), "Expecting a string for the directory name."
    assert isinstance(version, str), "Expecting a string for the version."
    status = getRepositoriesStatus(repositories)
    for R, S in list(status.items()):
        if S['Dirty']:
            die("'{}' is in a dirty state. Refusing to freeze !".format(R))
    print('- Revision: {}'.format(version))
    print('  Modules:')
    for R, S in list(status.items()):
        print('    - Name: {}'.format(R))
        print('      URL: {}'.format(S['URL']))
        print('      Revision: {}'.format(S['SHA1']))

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

    rv = 0
    if args.action == 'status':
        rv = printRepositoriesStatus(args.repositories)
        sys.exit(rv)
    elif args.action == 'freeze':
        rv = freezeRepositories(args.repositories, args.revision)
        sys.exit(rv)

    versions = getAllVersions(args.versions)

    # Make sure the requested version actually exists
    if args.revision not in versions:
        die("revision '{}' is unknown !".format(args.revision))

    if args.action == 'list':
        rv = printVersions(versions, args.verbose)
    elif args.action == 'check':
        rv = checkRepositoriesStatus(args.repositories, versions[args.revision])
    elif args.action == 'clone':
        rv = cloneRepositories(args.repositories, versions[args.revision], args.patches)
    else:
        die("Error ! Unsupported command '{}' !".format(args.action))

    sys.exit(rv)

if __name__ == '__main__':
        main()
