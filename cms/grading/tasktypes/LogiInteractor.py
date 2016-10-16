#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# The Game task type
# Author: Konstantin Tretyakov
# License: MIT or GNU Affero

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging

from cms import LANGUAGES, LANGUAGE_TO_SOURCE_EXT_MAP, \
    LANGUAGE_TO_HEADER_EXT_MAP
from cms import LANG_JAVA, LANG_CS
from cms.grading import get_compilation_commands, get_evaluation_commands, \
    compilation_step, evaluation_step, human_evaluation_message, \
    is_evaluation_passed, extract_outcome_and_text, white_diff_step
from cms.grading.ParameterTypes import ParameterTypeCollection, \
    ParameterTypeChoice, ParameterTypeString
from cms.grading.TaskType import TaskType, \
    create_sandbox, delete_sandbox
from cms.db import Executable


logger = logging.getLogger(__name__)

from cms.grading.tasktypes.Batch import Batch

# Dummy function to mark translatable string.
def N_(message):
    return message


class LogiInteractor(Batch):
    """Task type class for a unique standalone submission source, 
    that will be evaluated interactively using a special interactor.

    """
    ALLOW_PARTIAL_SUBMISSION = False

    _COMPILATION = ParameterTypeChoice(
        "Compilation",
        "compilation",
        "",
        {"alone": "Submissions are self-sufficient",
         "grader": "Submissions are compiled with a grader"})

    ACCEPTED_PARAMETERS = [_COMPILATION]

    @property
    def name(self):
        return "LogiInteractor"

    def evaluate(self, job, file_cacher):
        """See TaskType.evaluate."""
        # Create the sandbox
        sandbox = create_sandbox(file_cacher)

        # Prepare the execution
        executable_filename = job.executables.keys()[0]
        language = job.language
        if job.language == LANG_JAVA: # Somewhy JVM will only work with 9 processes or more
            sandbox.max_processes = 20+2
        elif job.language == LANG_CS: # And C# needs at least 2
            sandbox.max_processes = 5+2
        else:
            sandbox.max_processes = 1+2

        commands = get_evaluation_commands(language, executable_filename, job)
        commands = [["/usr/local/bin/pipexec", "--", "[A", "/usr/local/bin/logi_interactor", "input.txt", "output.txt", "]", "[B"] + commands[0] + ["]", "{A:1>B:0}", "{B:1>A:0}"]]
        executables_to_get = {
            executable_filename:
            job.executables[executable_filename].digest
            }
        input_filename = 'input.txt'
        output_filename = "output.txt"
        stdout_redirect = output_filename
        files_to_get = {
            input_filename: job.input
            }

        # Put the required files into the sandbox
        for filename, digest in executables_to_get.iteritems():
            sandbox.create_file_from_storage(filename, digest, executable=True)
        for filename, digest in files_to_get.iteritems():
            sandbox.create_file_from_storage(filename, digest, executable=True)

        # Actually performs the execution
        memory_limit = job.memory_limit
        if language == LANG_JAVA:
            memory_limit = 0  # JVM is unhappy with that, we'll use -Xmx option instead
        elif language == LANG_CS:
            memory_limit += 100  # It seems that mono needs an extra 100 or so MB to feel happy
        success, plus = evaluation_step(
            sandbox,
            commands,
            job.time_limit,
            memory_limit,
            stdin_redirect=None,
            stdout_redirect=stdout_redirect)

        job.sandboxes = [sandbox.path]
        job.plus = plus

        outcome = None
        text = None

        # Error in the sandbox: nothing to do!
        if not success:
            pass

        # Contestant's error: the marks won't be good
        elif not is_evaluation_passed(plus):
            outcome = 0.0
            text = human_evaluation_message(plus)
            if job.get_output:
                job.user_output = None

        # Otherwise, advance to checking the solution
        else:

            # Check that the output file was created
            if not sandbox.file_exists(output_filename):
                outcome = 0.0
                text = [N_("Evaluation didn't produce file %s"),
                        output_filename]
                if job.get_output:
                    job.user_output = None

            else:
                # If asked so, put the output file into the storage
                if job.get_output:
                    job.user_output = sandbox.get_file_to_storage(
                        output_filename,
                        "Output file in job %s" % job.info,
                        trunc_len=100 * 1024)

                # If just asked to execute, fill text and set dummy
                # outcome.
                if job.only_execution:
                    outcome = 0.0
                    text = [N_("Execution completed successfully")]

                # Otherwise evaluate the output file.
                else:

                    # Put the reference solution into the sandbox
                    sandbox.create_file_from_storage(
                        "res.txt",
                        job.output)

                    # Check the solution with white_diff
                    outcome, text = white_diff_step(
                           sandbox, output_filename, "res.txt")


        # Whatever happened, we conclude.
        job.success = success
        job.outcome = "%s" % outcome if outcome is not None else None
        job.text = text

        delete_sandbox(sandbox)
