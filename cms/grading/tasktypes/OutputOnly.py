#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2010-2012 Giovanni Mascellani <mascellani@poisson.phc.unipi.it>
# Copyright © 2010-2018 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2010-2012 Matteo Boscariol <boscarim@hotmail.com>
# Copyright © 2012-2013 Luca Wehrstedt <luca.wehrstedt@gmail.com>
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

"""Task type for output only tasks.

"""

import json
import logging
import os
import subprocess
import tempfile

from cms import config
from cms.grading.Job import Job
from cms.grading.ParameterTypes import ParameterTypeChoice
from . import TaskType, eval_output


logger = logging.getLogger(__name__)


# Dummy function to mark translatable string.
def N_(message):
    return message


class OutputOnly(TaskType):
    """Task type class for output only tasks, with submission composed
    of testcase_number text files, to be evaluated diffing or using a
    comparator.

    Parameters are a list of string with one element (for future
    possible expansions), which maybe 'diff' or 'comparator', meaning that
    the evaluation is done via white diff or via a comparator.

    """
    # Codename of the checker, if it is used.
    CHECKER_CODENAME = "checker"
    # Template for the filename of the output files provided by the user; %s
    # represent the testcase codename.
    USER_OUTPUT_FILENAME_TEMPLATE = "output_%s.txt"

    # Constants used in the parameter definition.
    OUTPUT_EVAL_DIFF = "diff"
    OUTPUT_EVAL_CHECKER = "comparator"
    OUTPUT_EVAL_TRUSTED_CHECKER = "trusted_checker"

    # Other constants to specify the task type behaviour and parameters.
    ALLOW_PARTIAL_SUBMISSION = True

    _EVALUATION = ParameterTypeChoice(
        "Output evaluation",
        "output_eval",
        "",
        {OUTPUT_EVAL_DIFF: "Outputs compared with white diff",
         OUTPUT_EVAL_CHECKER: "Outputs are compared by a comparator",
         OUTPUT_EVAL_TRUSTED_CHECKER: "Outputs are compared by trusted checker"})

    ACCEPTED_PARAMETERS = [_EVALUATION]

    @property
    def name(self):
        """See TaskType.name."""
        # TODO add some details if a comparator is used, etc...
        return "Output only"

    testable = False

    def __init__(self, parameters):
        super().__init__(parameters)
        self.output_eval: str = self.parameters[0]

    def get_compilation_commands(self, submission_format):
        """See TaskType.get_compilation_commands."""
        return None

    def get_user_managers(self):
        """See TaskType.get_user_managers."""
        return []

    def get_auto_managers(self):
        """See TaskType.get_auto_managers."""
        return []

    def _uses_checker(self) -> bool:
        return self.output_eval == OutputOnly.OUTPUT_EVAL_CHECKER

    @staticmethod
    def _get_user_output_filename(job: Job):
        return OutputOnly.USER_OUTPUT_FILENAME_TEMPLATE % \
            job.operation.testcase_codename

    def compile(self, job, file_cacher):
        """See TaskType.compile."""
        # No compilation needed.
        job.success = True
        job.compilation_success = True
        job.text = [N_("No compilation needed")]
        job.plus = {}

    def evaluate(self, job, file_cacher):
        """See TaskType.evaluate."""
        user_output_filename = self._get_user_output_filename(job)

        # Since we allow partial submission, if the file is not
        # present we report that the outcome is 0.
        if user_output_filename not in job.files:
            job.success = True
            job.outcome = "0.0"
            job.text = [N_("File not submitted")]
            job.plus = {}
            return

        if self.output_eval == OutputOnly.OUTPUT_EVAL_TRUSTED_CHECKER:
            with tempfile.TemporaryDirectory(dir=config.global_.temp_dir, prefix="cms-trusted-check-") as tmp:
                file_cacher.get_file_to_path(job.input, tmp + "/input")
                file_cacher.get_file_to_path(job.output, tmp + "/output")
                file_cacher.get_file_to_path(job.files[user_output_filename].digest, tmp + "/user_out")
                file_cacher.get_file_to_path(job.managers[OutputOnly.CHECKER_CODENAME].digest, tmp + "/checker")
                os.chmod(tmp + "/checker", 0o775)
                box_id_start = (file_cacher.service.shard + 1) * 1000
                try:
                    p = subprocess.run(
                        ["./checker", str(box_id_start)],
                        cwd=tmp,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=True,
                        timeout=60,
                    )
                    stdout_str = p.stdout.decode("utf-8")
                    result = json.loads(stdout_str)
                except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as e:
                    logger.error("trusted checker failed", exc_info=True)
                    if isinstance(e, subprocess.CalledProcessError):
                        logger.error("trusted stderr: %r", e.stderr)
                    job.success = False
                    job.text = ["internal error in checker"]
                    return

            job.success = result["success"]
            job.outcome = str(result["outcome"])
            job.text = result["text"]
            job.admin_text = result.get("admin_text")
            job.plus = result.get("stats", {})
            return

        # First and only step: eval the user output.
        box_success, outcome, text, admin_text = eval_output(
            file_cacher, job, 0,
            OutputOnly.CHECKER_CODENAME if self._uses_checker() else None,
            user_output_digest=job.files[user_output_filename].digest)

        # Fill in the job with the results.
        job.success = box_success
        job.outcome = str(outcome) if outcome is not None else None
        job.text = text
        job.admin_text = admin_text
        # There is no actual evaluation, so no statistics.
        job.plus = {} if box_success else None
