#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from cms.grading.scoretypes.GroupSum import GroupSum

import logging
log = logging.getLogger(__name__)

class GroupSumCond(GroupSum):
    """The score of a submission is the sum of group scores,
    and each group score is the sum of testcase scores in the group,
    except the scores for "conditional" groups are only given if the
    solution gets at least some points for the "unconditional" groups.
    Parameters are [[m, t, f], ... ]. See ScoreTypeGroup for m and t.
    The flag f must be one of "U", "C", "E":
    "U" for unconditional group whose score is always counted,
    "C" for conditional group whose score is only counted
    if the total for unconditional scores is non-zero,
    "E" for examples (these typically don't score points, but even
    if they do, they do not affect the conditional groups).

    """

    def max_scores(self):
        score, public_score, headers = GroupSum.max_scores(self)
        for st_idx, parameter in enumerate(self.parameters):
            if parameter[2] == "C":
                headers[st_idx] += " ***"
        return score, public_score, headers

    def compute_score(self, submission_result):
        score, subtasks, public_score, public_subtasks, ranking_details = GroupSum.compute_score(self, submission_result)
        if len(subtasks) == len(self.parameters):
            u_score = 0
            for st_idx, parameter in enumerate(self.parameters):
                if parameter[2] == "U":
                    u_score += subtasks[st_idx]["score_fraction"] * parameter[0]
            if u_score == 0:
                for st_idx, parameter in enumerate(self.parameters):
                    if parameter[2] == "C":
                        st_score = subtasks[st_idx]["score_fraction"] * parameter[0]
                        score -= st_score
                        if public_subtasks[st_idx] == subtasks[st_idx]:
                            public_score -= st_score
                        ranking_details[st_idx] = "0"
                        subtasks[st_idx]["score_ignore"] = True
        return score, subtasks, public_score, public_subtasks, ranking_details
