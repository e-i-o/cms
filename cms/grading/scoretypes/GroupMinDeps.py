#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2010-2012 Giovanni Mascellani <mascellani@poisson.phc.unipi.it>
# Copyright © 2010-2018 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2010-2012 Matteo Boscariol <boscarim@hotmail.com>
# Copyright © 2024 Tähvend Uustalu <thuustalu@gmail.com>
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

from cms.grading.scoretypes.GroupMin import GroupMin


class GroupMinDeps(GroupMin):
    """The score of a submission is the sum of the minimums of
    group scores. Additionally, every group may list a number of
    dependencies; in that case, points are awarded for that group
    only if the submission gets a nonzero score in each dependency.

    More specifically, for each group, its score_fraction AFTER is set to 0
    if, for any dependency, its score_fraction BEFORE was 0. No 'transitive
    closure' is calculated, you should recursively list all dependencies of
    dependencies manually if such behavior is desired.

    Parameters are [[m, t, p1, p2, ...], ... ]. See ScoreTypeGroup for m
    and t. p1, p2, ... can be strings of the form 'key:value'. This class
    recognizes two types of parameters:
     - name:group_name
     - deps:group1,group2,group3

    """

    @staticmethod
    def parse_parameters(parameters):
        parsed = {}
        for kv in parameters:
            if ":" not in kv:
                continue

            key, value = kv.split(":", 1)
            if key == "deps":
                parsed[key] = value.split(",")
            else:
                parsed[key] = value

        if "name" not in parsed:
            parsed["name"] = None
        if "deps" not in parsed:
            parsed["deps"] = []
        return parsed

    def compute_score(self, submission_result):
        score, subtasks, public_score, public_subtasks, ranking_details = GroupMin.compute_score(self, submission_result)
        if len(subtasks) == len(self.parameters):
            passed_subtasks = set()
            for st_idx, parameter in enumerate(self.parameters):
                name = self.parse_parameters(parameter)["name"]
                if bool(name) and subtasks[st_idx]["score_fraction"] > 0:
                    passed_subtasks.add(name)
            for st_idx, parameter in enumerate(self.parameters):
                failed_deps = False
                deps = self.parse_parameters(parameter)["deps"]

                for dep in deps:
                    if dep not in passed_subtasks:
                        failed_deps = True

                if failed_deps:
                    st_score = subtasks[st_idx]["score_fraction"] * parameter[0]
                    score -= st_score
                    if public_subtasks[st_idx] == subtasks[st_idx]:
                        public_score -= st_score
                    ranking_details[st_idx] = "0"
                    subtasks[st_idx]["score_ignore"] = True
                    # set score_fraction to 0 too to avoid max_subtask undoing our work here...
                    subtasks[st_idx]["score_fraction"] = 0.0
        return score, subtasks, public_score, public_subtasks, ranking_details
