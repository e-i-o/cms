#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2016-2017 Stefano Maggiolo <s.maggiolo@gmail.com>
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins.disabled import *  # noqa
from future.builtins import *  # noqa

from cms.grading.language import InterpretedLanguage


class PythonBase(InterpretedLanguage):
    """This defines a generic framework for handling the Python
    programming language.
    """

    @property
    def source_extensions(self):
        """See Language.source_extensions."""
        return [".py"]

    def get_compilation_commands(self,
            source_filenames, executable_filename,
            for_evaluation=True):
        """See Language.get_compilation_commands."""
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
