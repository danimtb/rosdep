# Copyright (c) 2024, JFrog, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Willow Garage, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# Author danimtb/danielm@jfrog.com

from __future__ import print_function

import json
import os
import subprocess

from ..core import InstallFailed
from ..installers import PackageManagerInstaller

# conan package manager key
CONAN_INSTALLER = 'conan'
CONAN_PROFILES = 'conan_profiles.json'
CONAN_LOCKFILE_NAME = 'rosdep_conan.lock'
CONAN_PROFILE_NAME = 'conan_profile'


def register_installers(context):
    context.set_installer(CONAN_INSTALLER, ConanInstaller())


def is_conan_installed():
    try:
        subprocess.Popen(['conan'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        return True
    except OSError:
        return False


def get_lockfile_path():
    return os.path.join("install", CONAN_LOCKFILE_NAME)


def get_profiles_path():
    return os.path.join("install", CONAN_PROFILES)


def get_profiles_data():
    conan_cmd = ['conan', 'profile', 'show', '--format', 'json']
    if os.path.exists(CONAN_PROFILE_NAME):
        conan_cmd.extend(['--profile', CONAN_PROFILE_NAME])
    output = subprocess.check_output(conan_cmd).strip().decode()
    return json.loads(output)


def conan_detect(pkgs):
    """
    Given a list of packages to install, return the list of packages already installed.

    This reads the packages installed from the conan lockfile.
    """
    if not is_conan_installed():
        return []

    if not os.path.exists(get_profiles_path()):
        return []

    if not os.path.exists(get_lockfile_path()):
        return []

    current_profile = get_profiles_data()

    with open(get_profiles_path()) as f:
        previous_profile = json.load(f)

    # If the profile to use in the install command does not match the previously used one, reinstall packages
    if current_profile != previous_profile:
        return []

    with open(get_lockfile_path()) as f:
        lockfile = json.load(f)

    installed_pkgs = [r.split("#")[0] for r in lockfile["requires"]]

    ret_list = []
    for pkg in pkgs:
        if pkg in installed_pkgs:
            ret_list.append(pkg)
    return ret_list


class ConanInstaller(PackageManagerInstaller):
    """
    :class:`Installer` support for conan.
    """

    def __init__(self):
        super(ConanInstaller, self).__init__(conan_detect, supports_depends=True)

    def get_version_strings(self):
        output = subprocess.check_output(['conan', 'version', '--format', 'json']).strip().decode()
        conan_version_data = json.loads(output)
        conan_version = conan_version_data["version"]
        return ['conan {}'.format(conan_version)]

    def _install_ament_generator(self, quiet=False):
        conan_config_install = ['conan', 'config', 'install']
        if quiet:
            conan_config_install.append('-vquiet')
        conan_config_install.extend(
            ['https://github.com/conan-io/conan-extensions.git', '--source-folder', 'extensions/generators'])
        subprocess.check_output(conan_config_install)

    def get_install_command(self, resolved, interactive=True, reinstall=False, quiet=False):
        if not is_conan_installed():
            raise InstallFailed((CONAN_INSTALLER, 'conan is not installed'))

        packages = self.get_packages_to_install(resolved, reinstall=reinstall)
        if not packages:
            return []

        profiles_path = get_profiles_path()
        os.makedirs(os.path.dirname(profiles_path), exist_ok=True)
        with open(profiles_path, 'a') as f:
            f.write(json.dumps(get_profiles_data()))

        self._install_ament_generator(quiet)

        conan_install = ["conan", "install"]
        if quiet:
            conan_install.append("-vquiet")
        if os.path.exists(CONAN_PROFILE_NAME):
            conan_install.extend(["--profile", CONAN_PROFILE_NAME])
        require_args = [f"--require {package}" for package in packages]
        require_str = " ".join(require_args)
        requires = require_str.split(" ")
        cmd = conan_install + requires + ["--update", "--generator", "Ament", "--build", "missing", "--output-folder", "install", "--lockfile-out", f"install/{CONAN_LOCKFILE_NAME}"]
        return [cmd]
