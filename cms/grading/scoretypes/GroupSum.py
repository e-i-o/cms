
#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from cms.grading.scoretypes.GroupMul import GroupMul

import logging
log = logging.getLogger(__name__)

class GroupSum(GroupMul):
    """The score of a submission is the sum of group scores,
    and each group score is the sum of testcase scores in the group.
    Parameters are [[m, t], ... ] (see ScoreTypeGroup).
    """

    def reduce(self, outcomes, parameter):
        return float(sum(outcomes))/len(outcomes)
