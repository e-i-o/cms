#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2010-2013 Giovanni Mascellani <mascellani@poisson.phc.unipi.it>
# Copyright © 2010-2018 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2010-2012 Matteo Boscariol <boscarim@hotmail.com>
# Copyright © 2012-2014 Luca Wehrstedt <luca.wehrstedt@gmail.com>
# Copyright © 2014 Artem Iglikov <artem.iglikov@gmail.com>
# Copyright © 2014 Fabian Gundlach <320pointsguy@gmail.com>
# Copyright © 2015 William Di Luigi <williamdiluigi@gmail.com>
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

"""Ranking-related handlers for AWS for a specific contest.

"""

import csv
import io

from sqlalchemy.orm import joinedload

from cms.db import Contest
from cms.grading.scoring import task_score
from .base import BaseHandler, require_permission


class RankingHandler(BaseHandler):
    """Shows the ranking for a contest.

    """
    @require_permission(BaseHandler.AUTHENTICATED)
    def get(self, contest_id, format, division=None):
        # This validates the contest id.
        self.safe_get_item(Contest, contest_id)

        # This massive joined load gets all the information which we will need
        # to generating the rankings.
        self.contest = self.sql_session.query(Contest)\
            .filter(Contest.id == contest_id)\
            .options(joinedload('participations'))\
            .options(joinedload('participations.submissions'))\
            .options(joinedload('participations.submissions.token'))\
            .options(joinedload('participations.submissions.results'))\
            .first()

        score_type = "sum"
        score_params = None
        if division is not None:
            div = {d.id: d for d in self.contest.divisions}.get(division)
            if div is not None:
                score_type = div.score_type
                score_params = div.score_type_parameters

        # Preprocess participations: get data about teams, scores
        show_teams = False
        show_tasks = []
        show_participants = []
        for task in self.contest.tasks:
            if division is None or task.divisions is None or division in task.divisions.split():
                show_tasks.append(task)

        for p in self.contest.participations:
            if division is not None and p.division is not None and p.division != division:
                continue
            if p.hidden:
                continue
            show_teams = show_teams or p.team_id

            p.scores = []
            total_score = 0.0
            partial = False
            score_nums = []
            for task in show_tasks:
                t_score, t_partial = task_score(p, task, rounded=True)
                score_nums.append(t_score)
                t_score_fmt = f"{t_score:.{task.score_precision}f}"
                p.scores.append((t_score_fmt, t_partial))
                partial = partial or t_partial

            if score_type == "top_n":
                sorted_scores = sorted(score_nums, reverse=True)
                total_score = sum(sorted_scores[:score_params])
            else:
                total_score = sum(score_nums)

            total_score = round(total_score, self.contest.score_precision)
            p.total_score = (total_score, partial)
            show_participants.append(p)

        show_participants.sort(key=lambda p: p.total_score, reverse=True)

        self.r_params = self.render_params()
        self.r_params["show_teams"] = show_teams
        self.r_params["show_tasks"] = show_tasks
        self.r_params["show_participants"] = show_participants
        self.r_params["download_link_suffix"] = []
        attachment_basename = "ranking"
        if division is not None:
            self.r_params["download_link_suffix"] = ["division", division]
            attachment_basename = "ranking_" + division
        if format == "txt":
            self.set_header("Content-Type", "text/plain")
            self.set_header("Content-Disposition",
                            f"attachment; filename=\"{attachment_basename}.txt\"")
            self.render("ranking.txt", **self.r_params)
        elif format == "csv":
            self.set_header("Content-Type", "text/csv")
            self.set_header("Content-Disposition",
                            f"attachment; filename=\"{attachment_basename}.csv\"")

            output = io.StringIO()  # untested
            writer = csv.writer(output)

            include_partial = True

            contest = self.r_params["contest"]

            row = ["Username", "User"]
            if show_teams:
                row.append("Team")
            for task in show_tasks:
                row.append(task.name)
                if include_partial:
                    row.append("P")

            row.append("Global")
            if include_partial:
                row.append("P")

            writer.writerow(row)

            for p in show_participants:

                row = [p.user.username,
                       "%s %s" % (p.user.first_name, p.user.last_name)]
                if show_teams:
                    row.append(p.team.name if p.team else "")
                for t_score, t_partial in p.scores:  # Custom field, see above
                    row.append(t_score)
                    if include_partial:
                        row.append("*" if t_partial else "")

                total_score, partial = p.total_score  # Custom field, see above
                row.append(total_score)
                if include_partial:
                    row.append("*" if partial else "")

                writer.writerow(row)  # untested

            self.finish(output.getvalue())
        else:
            self.render("ranking.html", **self.r_params)
