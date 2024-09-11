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
from ..shell_utils import read_stdout

# conan package manager key
CONAN_INSTALLER = 'conan'
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


def conan_detect(pkgs):
    """
    Given a list of packages to install, return the list of packages already installed.

    This reads the packages installed from the conan lockfile.
    """
    if not is_conan_installed():
        return []

    ret_list = []

    lockfile_path = os.path.join("install", CONAN_LOCKFILE_NAME)
    if not os.path.exists(lockfile_path):
        return ret_list

    data = {}
    with open(lockfile_path) as f:
        data = json.load(f)

    installed_pkgs = [r.split("#")[0] for r in data["requires"]]

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
        conan_version_str = subprocess.check_output(['conan', '--version']).strip().decode()
        conan_version = conan_version_str.replace("Conan version ", "")
        return ['conan {}'.format(conan_version)]

    def get_install_command(self, resolved, interactive=True, reinstall=False, quiet=False):
        if not is_conan_installed():
            raise InstallFailed((CONAN_INSTALLER, 'conan is not installed'))
        packages = self.get_packages_to_install(resolved, reinstall=reinstall)
        if not packages:
            return []

        conan_config_install = ['conan', 'config', 'install', 'https://github.com/conan-io/conan-extensions.git', '-a="--branch ament/folders"']
        conan_install = ["conan", "install"]
        if quiet:
            conan_install.append("-vquiet")
            conan_config_install.append("-vquiet")
        if os.path.exists(CONAN_PROFILE_NAME):
            conan_install.extend(["--profile", CONAN_PROFILE_NAME])
        subprocess.check_output(conan_config_install)
        require_args = [f"--require {package}" for package in packages]
        require_str = " ".join(require_args)
        requires = require_str.split(" ")
        cmd = conan_install + requires + ["--generator", "Ament", "--build", "missing", "--output-folder", "install", "--lockfile-out", f"install/{CONAN_LOCKFILE_NAME}"]
        return [self.elevate_priv(cmd)]
