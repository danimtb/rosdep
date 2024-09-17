import os
import unittest
from unittest.mock import patch


def get_test_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), 'conan'))


class TestConanDetect(unittest.TestCase):

    @patch("rosdep2.platforms.conan.is_conan_installed")
    @patch("rosdep2.platforms.conan.get_lockfile_path")
    def test_conan_detect_already_installed_packages(self, mock_get_lockfile_path, mock_is_conan_installed):
        from rosdep2.platforms.conan import conan_detect, CONAN_LOCKFILE_NAME

        mock_is_conan_installed.return_value = True
        mock_get_lockfile_path.return_value = os.path.join(get_test_dir(), CONAN_LOCKFILE_NAME)

        pkgs_to_install = ["zlib/1.3.1", "bzip2/1.0.8"]

        result = conan_detect(pkgs_to_install)
        self.assertEqual(pkgs_to_install, result)

    @patch("rosdep2.platforms.conan.is_conan_installed")
    @patch("rosdep2.platforms.conan.get_lockfile_path")
    def test_conan_detect_not_installed_packages(self, mock_get_lockfile_path, mock_is_conan_installed):
        from rosdep2.platforms.conan import conan_detect, CONAN_LOCKFILE_NAME

        mock_is_conan_installed.return_value = True
        mock_get_lockfile_path.return_value = os.path.join(get_test_dir(), CONAN_LOCKFILE_NAME)

        pkgs_to_install = ["this_is_not_installed", "this_isnt_installed_either"]

        result = conan_detect(pkgs_to_install)
        self.assertEqual([], result)
