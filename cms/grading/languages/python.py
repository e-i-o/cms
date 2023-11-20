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

"""Python programming language, generic base."""

from abc import abstractmethod
from cms.grading import Language


class PythonBase(Language):
    """This defines a generic framework for handling the Python
    programming language.
    """

    @property
    @abstractmethod
    def interpreter(self):
        """Path of the interpreter to use."""
        pass

    @property
    def source_extensions(self):
        """See Language.source_extensions."""
        return [".py"]

    def get_compilation_commands(self,
            source_filenames, executable_filename,
            for_evaluation=True):
        """See Language.get_compilation_commands."""
        # note: the zip still contains .py files.
        # we do the compile just to catch possible syntax errors.
        py_command = [self.interpreter, "-m", "py_compile"] + source_filenames
        zip_command = ["/bin/sh", "-c",
            " ".join(["/usr/bin/zip", "-q", "-"] + source_filenames +
                [">", executable_filename])]
        return [py_command, zip_command]

    def get_evaluation_commands(self,
            executable_filename, main=None, args=None):
        """See Language.get_evaluation_commands."""
        args = args if args is not None else []
        unzip_command = ["/usr/bin/unzip", executable_filename]
        py_command = [self.interpreter, main + ".py"] + args
        return [unzip_command, py_command]
