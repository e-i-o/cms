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

"""Python programming language, version 2, definition."""

from cms.grading.languages.python import PythonBase


__all__ = ["Python2CPython"]


class Python2CPython(PythonBase):
    """This defines the Python programming language, version 2 (more
    precisely, the subversion of Python 2 available on the system,
    usually 2.7) using the default interpeter in the system.

    """

    @property
    def interpreter(self):
        """See PythonBase.interpreter."""
        # ubuntu's python2.7 package doesn't provide plain python2.
        return "/usr/bin/python2.7"

    @property
    def name(self):
        """See Language.name."""
        return "Python 2 / CPython"
