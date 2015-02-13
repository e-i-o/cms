#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import json

from cms.grading.scoretypes.GroupSum import GroupSum

import logging
log = logging.getLogger(__name__)

class GroupSumAtLeastTwo(GroupSum):
    """The score of a submission is the sum of group scores,
    and each group score is the sum of testcase scores in the group.

    If the number of groups that have a nonzero score is 1, the whole solution
    gets a score of 0.

    Parameters are [[m, t], ... ] (see ScoreTypeGroup).

    """

    # This is a copy-paste from ScoreTypeGroup, with a single change 
    # in the last lines (which compute score)
    def compute_score(self, submission_result):
        """Compute the score of a submission.

        submission_id (int): the submission to evaluate.
        returns (float): the score

        """
        # Actually, this means it didn't even compile!
        if not submission_result.evaluated():
            return 0.0, "[]", 0.0, "[]", \
                json.dumps(["%lg" % 0.0 for _ in self.parameters])

        # XXX Lexicographical order by codename
        indices = sorted(self.public_testcases.keys())
        evaluations = dict((ev.codename, ev)
                           for ev in submission_result.evaluations)
        subtasks = []
        public_subtasks = []
        ranking_details = []
        tc_start = 0
        tc_end = 0

        for st_idx, parameter in enumerate(self.parameters):
            tc_end = tc_start + parameter[1]
            st_score = self.reduce([float(evaluations[idx].outcome)
                                    for idx in indices[tc_start:tc_end]],
                                   parameter) * parameter[0]
            st_public = all(self.public_testcases[idx]
                            for idx in indices[tc_start:tc_end])
            tc_outcomes = dict((
                idx,
                self.get_public_outcome(
                    float(evaluations[idx].outcome), parameter)
                ) for idx in indices[tc_start:tc_end])

            testcases = []
            public_testcases = []
            for idx in indices[tc_start:tc_end]:
                testcases.append({
                    "idx": idx,
                    "outcome": tc_outcomes[idx],
                    "text": evaluations[idx].text,
                    "time": evaluations[idx].execution_time,
                    "memory": evaluations[idx].execution_memory,
                    })
                if self.public_testcases[idx]:
                    public_testcases.append(testcases[-1])
                else:
                    public_testcases.append({"idx": idx})
            subtasks.append({
                "idx": st_idx + 1,
                "score": st_score,
                "max_score": parameter[0],
                "testcases": testcases,
                })
            if st_public:
                public_subtasks.append(subtasks[-1])
            else:
                public_subtasks.append({
                    "idx": st_idx + 1,
                    "testcases": public_testcases,
                    })

            ranking_details.append("%g" % round(st_score, 2))

            tc_start = tc_end

        score = sum(st["score"] for st in subtasks)
        public_score = sum(st["score"]
                           for st in public_subtasks
                           if "score" in st)

        # This is the only difference with the original
        # Here we check that at least two subtasks have nonzero score.
        # If not so, the whole score is 0.
        num_nonzero_groups = 0
        for st in subtasks:
            if (st["score"] > 0):
                num_nonzero_groups += 1
        if num_nonzero_groups <= 1:
            score = 0
            public_score = 0

        return score, json.dumps(subtasks), \
            public_score, json.dumps(public_subtasks), \
            json.dumps(ranking_details)


