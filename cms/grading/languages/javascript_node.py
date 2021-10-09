#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2016-2017 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2021 Ahto Truu <ahto.truu@ut.ee>
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

"""JavaScript programming language, via Node.JS."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins.disabled import *  # noqa
from future.builtins import *  # noqa

from cms.grading.language import InterpretedLanguage


class JavaScriptNode(InterpretedLanguage):
    """This defines the JavaScript programming language, interpreted with the
    Node.JS runtime.
    """

    @property
    def name(self):
        """See Language.name."""
        return "JavaScript"

    @property
    def source_extensions(self):
        """See Language.source_extensions."""
        return [".js"]

    @property
    def interpreter(self):
        return "/usr/bin/node"
