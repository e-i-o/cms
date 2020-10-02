#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from cms.grading.scoretypes.GroupSum import GroupSum

import logging
log = logging.getLogger(__name__)

class GroupSumCheck(GroupSum):
    """The score of a submission is the sum of group scores,
    and each group score is the sum of testcase scores in the group,
    except when any testcase scores is negative, the total for the
    whole group is zero.
    """

    def reduce(self, outcomes, parameter):
        if min(outcomes) < 0: return 0.0
        return float(sum(outcomes))/len(outcomes)
