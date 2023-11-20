#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2016-2018 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2019-2020 Ahto Truu <ahto.truu@ut.ee>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Python2 via PyPy"""

from cms.grading.languages.python import PythonBase


__all__ = ["Python2Pypy"]


class Python2Pypy(PythonBase):
    """This defines the Python 2 programming language, interpreted with the
    sytemwide PyPy interpreter.
    """

    @property
    def interpreter(self):
        """See PythonBase.interpreter."""
        # the ubuntu "pypy" package installs a python2.7 pypy interpreter here.
        # this might change, but at that point we should probably deprecate py2 altogether.
        return "/usr/bin/pypy"

    @property
    def name(self):
        return "Python 2 / PyPy"
