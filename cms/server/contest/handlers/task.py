#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2010-2014 Giovanni Mascellani <mascellani@poisson.phc.unipi.it>
# Copyright © 2010-2018 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2010-2012 Matteo Boscariol <boscarim@hotmail.com>
# Copyright © 2012-2018 Luca Wehrstedt <luca.wehrstedt@gmail.com>
# Copyright © 2013 Bernard Blackham <bernard@largestprime.net>
# Copyright © 2014 Artem Iglikov <artem.iglikov@gmail.com>
# Copyright © 2014 Fabian Gundlach <320pointsguy@gmail.com>
# Copyright © 2015-2016 William Di Luigi <williamdiluigi@gmail.com>
# Copyright © 2016 Amir Keivan Mohtashami <akmohtashami97@gmail.com>
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

"""Task-related handlers for CWS.

"""

import logging

from .base import BaseHandler

try:
    import tornado4.web as tornado_web
except ImportError:
    import tornado.web as tornado_web

from cms.server import multi_contest
from cmscommon.mimetypes import get_type_for_file_name
from .contest import ContestHandler, FileHandler
from ..phase_management import actual_phase_required


logger = logging.getLogger(__name__)


class TaskDescriptionHandler(ContestHandler):
    """Shows the data of a task in the contest.

    """
    @tornado_web.authenticated
    @actual_phase_required(0, 3)
    @multi_contest
    def get(self, task_name):
        task = self.get_task(task_name)
        if task is None:
            raise tornado_web.HTTPError(404)

        self.render("task_description.html", task=task, **self.r_params)


class TaskStatementViewHandler(FileHandler):
    """Shows the statement file of a task in the contest.

    logic:
    - /tasks/(taskname)/statements/(langcode)/(taskname).(langcode).pdf returns the PDF
    - /tasks/(taskname)/statements/(langcode),
    - /tasks/(taskname)/statements/(langcode)/literally/anything/ all redirect to the URL that returns the PDF

    Why? Because the thing at the end of the path will be offered as the filename when downloading the thing
    """
    @tornado_web.authenticated
    @actual_phase_required(0, 3)
    @multi_contest
    def get(self, task_name, suffix):
        task = self.get_task(task_name)
        if task is None:
            raise tornado_web.HTTPError(404)

        if "/" not in suffix:
            lang_code = suffix
            suffix = ""
        else:
            lang_code, suffix = suffix.split("/", 1)

        if lang_code not in task.statements:
            raise tornado_web.HTTPError(404)

        canonical_filename = "%s.%s.pdf" % (task.name, lang_code)
        if suffix != canonical_filename:
            self.sql_session.close()
            self.redirect(self.contest_url("tasks", task.name, "statements", lang_code, canonical_filename))
            return

        statement = task.statements[lang_code].digest
        self.sql_session.close()

        self.fetch(statement, "application/pdf", None)


class TaskAttachmentViewHandler(FileHandler):
    """Shows an attachment file of a task in the contest.

    """
    @tornado_web.authenticated
    @actual_phase_required(0, 3)
    @multi_contest
    def get(self, task_name, filename):
        task = self.get_task(task_name)
        if task is None:
            raise tornado_web.HTTPError(404)

        if filename not in task.attachments:
            raise tornado_web.HTTPError(404)

        attachment = task.attachments[filename].digest
        self.sql_session.close()

        mimetype = get_type_for_file_name(filename)
        if mimetype is None:
            mimetype = 'application/octet-stream'

        self.fetch(attachment, mimetype, filename)
