#
# Copyright 2015 Free Software Foundation, Inc.
#
# This file is part of PyBOMBS
#
# PyBOMBS is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# PyBOMBS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyBOMBS; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#
"""
Packager: yum
"""

import re
import subprocess
from pybombs.packagers.base import PackagerBase
from pybombs.utils import sysutils
from pybombs.utils.vcompare import vcompare

class Yum(PackagerBase):
    """
    yum install xyz
    """
    name = 'yum'
    pkgtype = 'rpm'

    def __init__(self):
        PackagerBase.__init__(self)

    def supported(self):
        """
        Check if we can even run apt-get.
        Return True if so.
        """
        return sysutils.which('yum') is not None

    def _package_install(self, pkgname, comparator=">=", required_version=None):
        """
        Call 'yum install pkgname' if we can satisfy the version requirements.
        """
        available_version = self.get_available_version_from_yum(pkgname)
        if required_version is not None and not vcompare(comparator, available_version, required_version):
            return False
        try:
            sysutils.monitor_process(["sudo", "yum", "-y", "install", pkgname])
            return True
        except Exception as ex:
            self.log.error("Running `yum install' failed.")
            self.log.obnoxious(str(ex))
        return False

    def _package_installed(self, pkgname, comparator=">=", required_version=None):
        """
        See if the installed version of pkgname matches the version requirements.
        """
        installed_version = self.get_installed_version_from_yum(pkgname)
        if not installed_version:
            return False
        if required_version is None:
            return True
        return vcompare(comparator, installed_version, required_version)

    def _package_exists(self, pkgname, comparator=">=", required_version=None):
        """
        See if an installable version of pkgname matches the version requirements.
        """
        available_version = self.get_available_version_from_yum(pkgname)
        if required_version is not None and not vcompare(comparator, available_version, required_version):
            return False
        return available_version

    ### yum specific functions:
    def get_available_version_from_yum(self, pkgname):
        """
        Check which version is available in yum.
        """
        try:
            out = subprocess.check_output(["yum", "info", pkgname]).strip()
            if len(out) == 0:
                self.log.debug("Did not expect empty output for `yum info'...")
                return False
            ver = re.search(r'^Version\s+:\s+(?P<ver>.*$)', out, re.MULTILINE).group('ver')
            self.log.debug("Package {} has version {} in yum".format(pkgname, ver))
            return ver
        except subprocess.CalledProcessError as ex:
            # This usually means the package was not found, so don't worry
            self.log.obnoxious("`yum info' returned non-zero exit status.")
            self.log.obnoxious(str(ex))
            return False
        except Exception as ex:
            self.log.error("Error parsing yum info")
            self.log.error(str(ex))
        return False

    def get_installed_version_from_yum(self, pkgname):
        """
        Check which version is currently installed.
        """
        try:
            # yum list installed will return non-zero if package does not exist, thus will throw
            out = subprocess.check_output(
                    ["yum", "list", "installed", pkgname],
                    stderr=subprocess.STDOUT
            ).strip().split("\n")
            # Output looks like this:
            # <pkgname>.<arch>   <version>   <more info>
            # So, two steps:
            # 1) Check that pkgname is correct
            # 2) return version
            for line in out:
                mobj = re.match(r"^(?P<pkg>[^\.]+)\.(?P<arch>\S+)\s+(?P<ver>[0-9]+(\.[0-9]+){0,2})", line)
                if mobj and mobj.group('pkg') == pkgname:
                    ver = mobj.group('ver')
                    self.log.debug("Package {} has version {} in yum".format(pkgname, ver))
                    return ver
            return False
        except subprocess.CalledProcessError:
            # This usually means the packet is not installed
            return False
        except Exception as ex:
            self.log.error("Parsing `yum list installed` failed.")
            self.log.obnoxious(str(ex))
        return False


