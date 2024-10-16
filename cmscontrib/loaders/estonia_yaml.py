#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2010-2014 Giovanni Mascellani <mascellani@poisson.phc.unipi.it>
# Copyright © 2010-2018 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2010-2012 Matteo Boscariol <boscarim@hotmail.com>
# Copyright © 2013-2018 Luca Wehrstedt <luca.wehrstedt@gmail.com>
# Copyright © 2014-2018 William Di Luigi <williamdiluigi@gmail.com>
# Copyright © 2015-2019 Luca Chiodini <luca@chiodini.org>
# Copyright © 2016 Andrea Cracco <guilucand@gmail.com>
# Copyright © 2018 Edoardo Morassutto <edoardo.morassutto@gmail.com>
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

import datetime
import logging
import os
import os.path
import sys
from datetime import timedelta
import glob
import subprocess

import yaml

from cms import TOKEN_MODE_DISABLED, TOKEN_MODE_FINITE, TOKEN_MODE_INFINITE, \
    FEEDBACK_LEVEL_FULL, FEEDBACK_LEVEL_RESTRICTED
from cms.db import Contest, User, Task, Statement, Attachment, Team, Dataset, \
    Manager, Testcase, SolutionTemplate
from cms.db.contest import Division
from cms.grading import languagemanager
from cms.grading.languagemanager import LANGUAGES, HEADER_EXTS
from cmscommon.constants import \
    SCORE_MODE_MAX, SCORE_MODE_MAX_SUBTASK, SCORE_MODE_MAX_TOKENED_LAST
from cmscommon.crypto import build_password, generate_random_password
from cmscontrib import touch
from .base_loader import ContestLoader, TaskLoader, UserLoader, TeamLoader


logger = logging.getLogger(__name__)


# Patch PyYAML to make it load all strings as unicode instead of str
# (see http://stackoverflow.com/questions/2890146).
def construct_yaml_str(self, node):
    return self.construct_scalar(node)


yaml.Loader.add_constructor("tag:yaml.org,2002:str", construct_yaml_str)
yaml.SafeLoader.add_constructor("tag:yaml.org,2002:str", construct_yaml_str)
# i REALLY hope this is unnecessary now???

def getmtime(fname):
    return os.stat(fname).st_mtime


def load_yaml_from_path(path):
    with open(path, "rt", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load(src, dst, src_name, dst_name=None, conv=lambda i: i):
    """Execute:
      dst[dst_name] = conv(src[src_name])
    with the following features:

      * If src_name is a list, it tries each of its element as
        src_name, stopping when the first one succedes.

      * If dst_name is None, it is set to src_name; if src_name is a
        list, dst_name is set to src_name[0] (_not_ the one that
        succedes).

      * By default conv is the identity function.

      * If dst is None, instead of assigning the result to
        dst[dst_name] (which would cast an exception) it just returns
        it.

      * If src[src_name] doesn't exist, the behavior is different
        depending on whether dst is None or not: if dst is None,
        conv(None) is returned; if dst is not None, nothing is done
        (in particular, dst[dst_name] is _not_ assigned to conv(None);
        it is not assigned to anything!).

    """
    if dst is not None and dst_name is None:
        if isinstance(src_name, list):
            dst_name = src_name[0]
        else:
            dst_name = src_name
    res = None
    found = False
    if isinstance(src_name, list):
        for this_src_name in src_name:
            try:
                res = src[this_src_name]
            except KeyError:
                pass
            else:
                found = True
                break
    else:
        if src_name in src:
            found = True
            res = src[src_name]
    if dst is not None:
        if found:
            dst[dst_name] = conv(res)
    else:
        return conv(res)


def make_timedelta(t):
    return timedelta(seconds=t)

def parse_datetime(v):
    if isinstance(v, int) or isinstance(v, float):
        return datetime.datetime.utcfromtimestamp(v)
    return datetime.datetime.fromisoformat(v)

class EstYamlLoader(ContestLoader, TaskLoader, UserLoader, TeamLoader):
    """Load a contest, task, user or team stored using the Italian IOI format.

    Given the filesystem location of a contest, task, user or team, stored
    using the Italian IOI format, parse those files and directories to produce
    data that can be consumed by CMS, i.e. the corresponding instances of the
    DB classes.

    """

    short_name = 'estonia_yaml'
    description = 'Estonian YAML-based format (based on Italy)'

    @staticmethod
    def detect(path):
        """See docstring in class Loader."""
        # TODO - Not really refined...
        return os.path.exists(os.path.join(path, "contest.yaml")) or \
            os.path.exists(os.path.join(path, "task.yaml")) or \
            os.path.exists(os.path.join(os.path.dirname(path), "contest.yaml"))

    def get_task_loader(self, taskname):
        return EstYamlLoader(os.path.join(self.path, taskname), self.file_cacher)

    def get_contest(self):
        """See docstring in class ContestLoader."""
        if not os.path.exists(os.path.join(self.path, "contest.yaml")):
            logger.critical("File missing: \"contest.yaml\"")
            return None

        conf = load_yaml_from_path(os.path.join(self.path, "contest.yaml"))

        # Here we update the time of the last import
        touch(os.path.join(self.path, ".itime_contest"))
        # If this file is not deleted, then the import failed
        touch(os.path.join(self.path, ".import_error_contest"))

        args = {}

        load(conf, args, ["name", "nome_breve"])
        load(conf, args, ["description", "nome"])

        logger.info("Loading parameters for contest %s.", args["name"])

        # Use the new token settings format if detected.
        if "token_mode" in conf:
            load(conf, args, "token_mode")
            load(conf, args, "token_max_number")
            load(conf, args, "token_min_interval", conv=make_timedelta)
            load(conf, args, "token_gen_initial")
            load(conf, args, "token_gen_number")
            load(conf, args, "token_gen_interval", conv=make_timedelta)
            load(conf, args, "token_gen_max")
        # Otherwise fall back on the old one.
        else:
            logger.warning(
                "contest.yaml uses a deprecated format for token settings "
                "which will soon stop being supported, you're advised to "
                "update it.")
            # Determine the mode.
            if conf.get("token_initial", None) is None:
                args["token_mode"] = TOKEN_MODE_DISABLED
            elif conf.get("token_gen_number", 0) > 0 and \
                    conf.get("token_gen_time", 0) == 0:
                args["token_mode"] = TOKEN_MODE_INFINITE
            else:
                args["token_mode"] = TOKEN_MODE_FINITE
            # Set the old default values.
            args["token_gen_initial"] = 0
            args["token_gen_number"] = 0
            args["token_gen_interval"] = timedelta()
            # Copy the parameters to their new names.
            load(conf, args, "token_total", "token_max_number")
            load(conf, args, "token_min_interval", conv=make_timedelta)
            load(conf, args, "token_initial", "token_gen_initial")
            load(conf, args, "token_gen_number")
            load(conf, args, "token_gen_time", "token_gen_interval",
                 conv=make_timedelta)
            load(conf, args, "token_max", "token_gen_max")
            # Remove some corner cases.
            if args["token_gen_initial"] is None:
                args["token_gen_initial"] = 0
            if args["token_gen_interval"].total_seconds() == 0:
                args["token_gen_interval"] = timedelta(minutes=1)

        load(conf, args, ["start", "inizio"], conv=parse_datetime)
        load(conf, args, ["stop", "fine"], conv=parse_datetime)
        load(conf, args, ["per_user_time"], conv=make_timedelta)
        load(conf, args, ["timezone"])

        load(conf, args, "max_submission_number")
        load(conf, args, "max_user_test_number")
        load(conf, args, "min_submission_interval", conv=make_timedelta)
        load(conf, args, "min_user_test_interval", conv=make_timedelta)

        tasks = load(conf, None, ["tasks", "problemi"])
        participations = load(conf, None, ["users", "utenti"])
        participations = [] if participations is None else participations
        for p in participations:
            if "password" in p:
                p["password"] = build_password(p["password"])

        divisions = {}
        for div in conf.get("divisions", []):
            score_mode = div.get("score_mode")
            if score_mode is None:
                score_type = "sum"
                score_type_parameters = None
            elif isinstance(score_mode, str):
                score_type = score_mode
                score_type_parameters = None
            else:
                assert isinstance(score_mode, list)
                assert len(score_mode) == 2
                score_type = score_mode[0]
                score_type_parameters = score_mode[1]
            the_d = Division(
                name=div["id"],
                display_name=div["display_name"],
                score_type=score_type,
                score_type_parameters=score_type_parameters)
            divisions[div["id"]] = the_d
        args["divisions"] = divisions

        # Import was successful
        os.remove(os.path.join(self.path, ".import_error_contest"))

        logger.info("Contest parameters loaded.")

        return Contest(**args), tasks, participations

    def post_contest_insertion(self, contest):
        # set contest score_precision to highest task's score_precision
        precision = 0
        for task in contest.tasks:
            precision = max(precision, task.score_precision)
        logger.info("set score_precision to %d", precision)
        contest.score_precision = precision

        # write contest ID to file for our helper script
        with open(os.path.join(self.path, ".inserted_contest_id"), 'w') as f:
            f.write(str(contest.id))

    def get_user(self):
        """See docstring in class UserLoader."""

        if not os.path.exists(os.path.join(os.path.dirname(self.path),
                                           "contest.yaml")):
            logger.critical("File missing: \"contest.yaml\"")
            return None

        username = os.path.basename(self.path)
        logger.info("Loading parameters for user %s.", username)

        conf = load_yaml_from_path(
            os.path.join(os.path.dirname(self.path), "contest.yaml"))

        args = {}

        conf = load(conf, None, ["users", "utenti"])

        for user in conf:
            if user["username"] == username:
                conf = user
                break
        else:
            logger.critical("The specified user cannot be found.")
            return None

        load(conf, args, "username")
        load(conf, args, "password", conv=build_password)
        if "password" not in args:
            # this is the same as the default in db/user.py, but that default
            # doesn't seem to work...
            args["password"] = build_password(generate_random_password())

        load(conf, args, ["first_name", "nome"])
        load(conf, args, ["last_name", "cognome"])

        if "first_name" not in args:
            args["first_name"] = ""
        if "last_name" not in args:
            args["last_name"] = args["username"]

        logger.info("User parameters loaded.")

        return User(**args)

    def get_team(self):
        """See docstring in class TeamLoader."""

        if not os.path.exists(os.path.join(os.path.dirname(self.path),
                                           "contest.yaml")):
            logger.critical("File missing: \"contest.yaml\"")
            return None

        team_code = os.path.basename(self.path)
        logger.info("Loading parameters for team %s.", team_code)

        conf = load_yaml_from_path(
            os.path.join(os.path.dirname(self.path), "contest.yaml"))

        args = {}

        conf = load(conf, None, "teams")

        for team in conf:
            if team["code"] == team_code:
                conf = team
                break
        else:
            logger.critical("The specified team cannot be found.")
            return None

        load(conf, args, "code")
        load(conf, args, "name")

        logger.info("Team parameters loaded.")

        return Team(**args)

    def get_task(self, get_statement=True):
        """See docstring in class TaskLoader."""
        name = os.path.split(self.path)[1]

        if (not os.path.exists(os.path.join(self.path, "task.yaml"))) and \
           (not os.path.exists(os.path.join(self.path, "..", name + ".yaml"))):
            logger.critical("File missing: \"task.yaml\"")
            return None

        # We first look for the yaml file inside the task folder,
        # and eventually fallback to a yaml file in its parent folder.
        try:
            conf = load_yaml_from_path(os.path.join(self.path, "task.yaml"))
        except OSError as err:
            try:
                deprecated_path = os.path.join(self.path, "..", name + ".yaml")
                conf = load_yaml_from_path(deprecated_path)

                logger.warning("You're using a deprecated location for the "
                               "task.yaml file. You're advised to move %s to "
                               "%s.", deprecated_path,
                               os.path.join(self.path, "task.yaml"))
            except OSError:
                # Since both task.yaml and the (deprecated) "../taskname.yaml"
                # are missing, we will only warn the user that task.yaml is
                # missing (to avoid encouraging the use of the deprecated one)
                raise err
        # If this file is not deleted, then the import failed
        # This is done before `make` so that `make` failures are considered errors.
        touch(os.path.join(self.path, ".import_error"))

        # Update checkers if necessary
        if os.path.exists(os.path.join(self.path, "check", "Makefile")):
            logger.info("Running `make` to update checkers for %s...", name)
            res = subprocess.run(["make"], cwd=os.path.join(self.path, "check"))
            if res.returncode != 0:
                logger.error("Error occurred when building checkers")
                sys.exit(1)

        # Here we update the time of the last import
        # This is done after `make` so that the files generated by make aren't considered to be changed.
        touch(os.path.join(self.path, ".itime"))

        args = {}

        load(conf, args, ["name", "nome_breve"])
        load(conf, args, ["title", "nome"])

        if name != args["name"]:
            logger.info("The task name (%s) and the directory name (%s) are "
                        "different. The former will be used.", args["name"],
                        name)

        if args["name"] == args["title"]:
            logger.warning("Short name equals long name (title). "
                           "Please check.")

        name = args["name"]

        logger.info("Loading parameters for task %s.", name)

        if get_statement:
            primary_language = load(conf, None, "primary_language")
            if primary_language is None:
                primary_language = 'et'
            statement_paths = glob.glob("%s/statement/statement.*.pdf" % (self.path))
            languages = []
            statements = {}

            if len(statement_paths) == 0:
                logger.warning("No statements found!")
            for s in statement_paths:
                 lang = s.split(".")[-2]
                 languages.append(lang)
                 digest = self.file_cacher.put_file_from_path(s, "Statement for task %s (language %s)" % (name, lang))
                 statements[lang] = (Statement(lang, digest))
                 logger.info("Loaded statement for language %s" % lang)

            args["statements"] = statements
            args["primary_statements"] = [primary_language]
            args["attachments"] = []  # FIXME Use auxiliary

        args["submission_format"] = ["%s.%%l" % name]

        # Import the feedback level when explicitly set to full
        if conf.get("feedback_level", None) == FEEDBACK_LEVEL_FULL:
            args["feedback_level"] = FEEDBACK_LEVEL_FULL
        elif conf.get("feedback_level", None) == FEEDBACK_LEVEL_RESTRICTED:
            args["feedback_level"] = FEEDBACK_LEVEL_RESTRICTED
        else:
            # default to full feedback
            args["feedback_level"] = FEEDBACK_LEVEL_FULL

        if conf.get("score_mode", None) == SCORE_MODE_MAX:
            args["score_mode"] = SCORE_MODE_MAX
        elif conf.get("score_mode", None) == SCORE_MODE_MAX_SUBTASK:
            args["score_mode"] = SCORE_MODE_MAX_SUBTASK
        elif conf.get("score_mode", None) == SCORE_MODE_MAX_TOKENED_LAST:
            args["score_mode"] = SCORE_MODE_MAX_TOKENED_LAST
        else:
            # default to max-subtask
            args["score_mode"] = SCORE_MODE_MAX_SUBTASK

        # Use the new token settings format if detected.
        if "token_mode" in conf:
            load(conf, args, "token_mode")
            load(conf, args, "token_max_number")
            load(conf, args, "token_min_interval", conv=make_timedelta)
            load(conf, args, "token_gen_initial")
            load(conf, args, "token_gen_number")
            load(conf, args, "token_gen_interval", conv=make_timedelta)
            load(conf, args, "token_gen_max")
        # Otherwise fall back on the old one.
        else:
            # Determine the mode.
            if conf.get("token_initial", None) is None:
                args["token_mode"] = TOKEN_MODE_DISABLED
            else:
                logger.warning(
                    "task.yaml uses a deprecated format for token settings which "
                    "will soon stop being supported, you're advised to update it.")
                if conf.get("token_gen_number", 0) > 0 and \
                        conf.get("token_gen_time", 0) == 0:
                    args["token_mode"] = TOKEN_MODE_INFINITE
                else:
                    args["token_mode"] = TOKEN_MODE_FINITE
            # Set the old default values.
            args["token_gen_initial"] = 0
            args["token_gen_number"] = 0
            args["token_gen_interval"] = timedelta()
            # Copy the parameters to their new names.
            load(conf, args, "token_total", "token_max_number")
            load(conf, args, "token_min_interval", conv=make_timedelta)
            load(conf, args, "token_initial", "token_gen_initial")
            load(conf, args, "token_gen_number")
            load(conf, args, "token_gen_time", "token_gen_interval",
                 conv=make_timedelta)
            load(conf, args, "token_max", "token_gen_max")
            # Remove some corner cases.
            if args["token_gen_initial"] is None:
                args["token_gen_initial"] = 0
            if args["token_gen_interval"].total_seconds() == 0:
                args["token_gen_interval"] = timedelta(minutes=1)

        load(conf, args, "max_submission_number")
        load(conf, args, "max_user_test_number")
        load(conf, args, "min_submission_interval", conv=make_timedelta)
        load(conf, args, "min_user_test_interval", conv=make_timedelta)
        load(conf, args, "divisions")

        # Attachments
        args["attachments"] = dict()
        if os.path.exists(os.path.join(self.path, "att")):
            for filename in os.listdir(os.path.join(self.path, "att")):
                digest = self.file_cacher.put_file_from_path(
                    os.path.join(self.path, "att", filename),
                    "Attachment %s for task %s" % (filename, name))
                args["attachments"][filename] = Attachment(filename, digest)

        args["solution_templates"] = dict()
        for template_file in sorted(glob.glob("%s/templates/template*" % self.path)):
            template_basename = os.path.basename(template_file)
            lang = languagemanager.filename_to_language(template_file)
            if lang is None:
                logger.warning("Unknown file %s found in templates directory" % template_basename)
                continue
            if lang.name in args["solution_templates"]:
                logger.warning("Duplicate template %s for language %s - ignoring" % (template_basename, lang.name))
                continue
            with open(template_file) as f:
                content = f.read()
            args["solution_templates"][lang.name] = SolutionTemplate(lang.name, content)

        # Score precision.
        load(conf, args, "score_precision")

        task = Task(**args)

        args = {}
        args["task"] = task
        args["description"] = conf.get("version", "Default")
        args["autojudge"] = False

        load(conf, args, ["time_limit", "timeout"], conv=float)
        load(conf, args, ["time_limit_interpreted"], conv=float)
        # The Italian YAML format specifies memory limits in MiB.
        load(conf, args, ["memory_limit", "memlimit"],
             conv=lambda mb: mb * 1024 * 1024)
        load(conf, args, "score_type")

        # Builds the parameters that depend on the task type
        args["managers"] = []
        infile_param = conf.get("infile", "input.txt")
        outfile_param = conf.get("outfile", "output.txt")

        # If there is solution/grader.%l for some language %l, then,
        # presuming that the task type is Batch, we retrieve graders
        # in the form solution/grader.%l
        graders = False
        for lang in LANGUAGES:
            if os.path.exists(os.path.join(
                    self.path, "solution", "grader%s" % lang.source_extension)):
                graders = True
                break
        if graders:
            # Read grader for each language
            for lang in LANGUAGES:
                extension = lang.source_extension
                grader_filename = os.path.join(
                    self.path, "solution", "grader%s" % extension)
                if os.path.exists(grader_filename):
                    digest = self.file_cacher.put_file_from_path(
                        grader_filename,
                        "Grader for task %s and language %s" %
                        (task.name, lang.name))
                    args["managers"] += [
                        Manager("grader%s" % extension, digest)]
                else:
                    logger.warning("Grader for language %s not found", lang.name)
            # Read managers with other known file extensions
            for other_filename in os.listdir(os.path.join(self.path, "solution")):
                if any(other_filename.endswith(header)
                       for header in HEADER_EXTS):
                    digest = self.file_cacher.put_file_from_path(
                        os.path.join(self.path, "solution", other_filename),
                        "Manager %s for task %s" % (other_filename, task.name))
                    args["managers"] += [
                        Manager(other_filename, digest)]
            compilation_param = "grader"
        else:
            compilation_param = "alone"

        # If there is check/checker (or equivalent), then, presuming
        # that the task type is Batch or OutputOnly, we retrieve the
        # comparator
        paths = [os.path.join(self.path, "check", "checker"),
                 os.path.join(self.path, "cor", "correttore")]
        for path in paths:
            if os.path.exists(path):
                digest = self.file_cacher.put_file_from_path(
                    path,
                    "Manager for task %s" % task.name)
                args["managers"] += [
                    Manager("checker", digest)]
                evaluation_param = "comparator"
                break
        else:
            evaluation_param = "diff"

        # If there is check/batchmanager, then this is an interactive
        # task to be evaluated in a single sandbox
        paths = [os.path.join(self.path, "check", "batchmanager")]
        for path in paths:
            if os.path.exists(path):
                digest = self.file_cacher.put_file_from_path(
                    path,
                    "Manager for task %s" % task.name)
                args["managers"] += [
                    Manager("batchmanager", digest)]
                break

        # Detect subtasks by checking GEN
        gen_filename = os.path.join(self.path, 'gen', 'GEN')
        try:
            with open(gen_filename, "rt", encoding="utf-8") as gen_file:
                subtasks = []
                testcases = 0
                points = None
                parameters = []
                for line in gen_file:
                    line = line.strip()
                    splitted = line.split('#', 1)

                    if len(splitted) == 1:
                        # This line represents a testcase, otherwise
                        # it's just a blank
                        if splitted[0] != '':
                            testcases += 1

                    else:
                        testcase, comment = splitted
                        testcase = testcase.strip()
                        comment = comment.strip()
                        testcase_detected = len(testcase) > 0
                        copy_testcase_detected = comment.startswith("COPY:")
                        subtask_detected = comment.startswith('ST:')

                        flags = [testcase_detected,
                                 copy_testcase_detected,
                                 subtask_detected]
                        if len([x for x in flags if x]) > 1:
                            raise Exception("No testcase and command in"
                                            " the same line allowed")

                        # This line represents a testcase and contains a
                        # comment, but the comment doesn't start a new
                        # subtask
                        if testcase_detected or copy_testcase_detected:
                            testcases += 1

                        # This line starts a new subtask
                        if subtask_detected:
                            # Close the previous subtask
                            if points is None:
                                assert(testcases == 0)
                            else:
                                subtasks.append([points, testcases] + parameters)
                            # Open the new one
                            testcases = 0
                            comment = [x.strip() for x in comment[3:].split()]
                            points = int(comment[0])
                            parameters = comment[1:]

                # Close last subtask (if no subtasks were defined, just
                # fallback to Sum)
                if points is None:
                    assert args["score_type"] == "Sum"
                    total_value = float(conf.get("total_value", 100.0))
                    input_value = 0.0
                    n_input = testcases
                    if n_input != 0:
                        input_value = total_value / n_input
                    args["score_type_parameters"] = input_value
                else:
                    subtasks.append([points, testcases] + parameters)
                    #assert(100 == sum([int(st[0]) for st in subtasks]))
                    n_input = sum([int(st[1]) for st in subtasks])
                    #args["score_type"] = "GroupMin"
                    assert args["score_type"] in ["GroupMin", "GroupMinDeps", "GroupMul", "GroupSum", "GroupSumCond", "GroupSumCheck"]
                    if args["score_type"] == "GroupSumCond":
                        for st in subtasks:
                            assert len(st) >= 3
                            assert st[2] in ["E", "U", "C"]
                    args["score_type_parameters"] = subtasks

                if "n_input" in conf:
                    assert int(conf['n_input']) == n_input

        # If gen/GEN doesn't exist, just fallback to Sum
        except OSError:
            assert args["score_type"] == "Sum"
            total_value = float(conf.get("total_value", 100.0))
            input_value = 0.0
            n_input = int(conf['n_input'])
            if n_input != 0:
                input_value = total_value / n_input
            args["score_type_parameters"] = input_value

        # Override score_type if explicitly specified
        if "score_type" in conf and "score_type_parameters" in conf:
            logger.info("Overriding 'score_type' and 'score_type_parameters' "
                        "as per task.yaml")
            load(conf, args, "score_type")
            load(conf, args, "score_type_parameters")

        # If output_only is set, then the task type is OutputOnly
        if conf.get('output_only', False):
            args["task_type"] = "OutputOnly"
            args["time_limit"] = None
            args["time_limit_interpreted"] = None
            args["memory_limit"] = None
            args["task_type_parameters"] = [evaluation_param]
            task.submission_format = \
                ["output_%03d.txt" % i for i in range(n_input)]

        # If there is check/manager (or equivalent), then the task
        # type is Communication
        else:
            paths = [os.path.join(self.path, "check", "manager"),
                     os.path.join(self.path, "cor", "manager")]
            for path in paths:
                if os.path.exists(path):
                    num_processes = load(conf, None, "num_processes")
                    if num_processes is None:
                        num_processes = 1
                    io_type = load(conf, None, "user_io")
                    if io_type is not None:
                        if io_type not in ["std_io", "fifo_io"]:
                            logger.warning("user_io incorrect. Valid options "
                                           "are 'std_io' and 'fifo_io'. "
                                           "Ignored.")
                            io_type = None
                    logger.info("Task type Communication")
                    args["task_type"] = "Communication"
                    args["task_type_parameters"] = \
                        [num_processes, "alone", io_type or "std_io"]
                    digest = self.file_cacher.put_file_from_path(
                        path,
                        "Manager for task %s" % task.name)
                    args["managers"] += [
                        Manager("manager", digest)]
                    for lang in LANGUAGES:
                        stub_name = os.path.join(
                            self.path, "solution", "stub%s" % lang.source_extension)
                        if os.path.exists(stub_name):
                            digest = self.file_cacher.put_file_from_path(
                                stub_name,
                                "Stub for task %s and language %s" % (
                                    task.name, lang.name))
                            args["task_type_parameters"] = \
                                [num_processes, "stub", io_type or "fifo_io"]
                            args["managers"] += [
                                Manager(
                                    "stub%s" % lang.source_extension, digest)]
                        else:
                            logger.warning("Stub for language %s not "
                                           "found.", lang.name)
                    for other_filename in os.listdir(os.path.join(self.path,
                                                                  "solution")):
                        if any(other_filename.endswith(header)
                               for header in HEADER_EXTS):
                            digest = self.file_cacher.put_file_from_path(
                                os.path.join(self.path, "solution", other_filename),
                                "Stub %s for task %s" % (other_filename,
                                                         task.name))
                            args["managers"] += [
                                Manager(other_filename, digest)]
                    break

            # Otherwise, the task type is Batch
            else:
                args["task_type"] = "Batch"
                args["task_type_parameters"] = \
                    [compilation_param, [infile_param, outfile_param],
                     evaluation_param]

        args["testcases"] = []
        for i in range(n_input):
            input_digest = self.file_cacher.put_file_from_path(
                os.path.join(self.path, "input", "input%d.txt" % i),
                "Input %d for task %s" % (i, task.name))
            output_digest = self.file_cacher.put_file_from_path(
                os.path.join(self.path, "output", "output%d.txt" % i),
                "Output %d for task %s" % (i, task.name))
            args["testcases"] += [
                Testcase("%03d" % i, False, input_digest, output_digest)]
            if args["task_type"] == "OutputOnly":
                task.attachments.set(
                    Attachment("input_%03d.txt" % i, input_digest))
        public_testcases = load(conf, None, ["public_testcases", "risultati"],
                                conv=lambda x: "" if x is None else x)
        if public_testcases == "all":
            for t in args["testcases"]:
                t.public = True
        elif len(public_testcases) > 0:
            for x in public_testcases.split(","):
                if ".." in x:
                    frm, to = map(int, x.strip().split(".."))
                else:
                    frm = to = int(x.strip())
                for i in range(frm, to+1):
                    args["testcases"][i].public = True
        args["testcases"] = dict((tc.codename, tc) for tc in args["testcases"])
        args["managers"] = dict((mg.filename, mg) for mg in args["managers"])

        dataset = Dataset(**args)
        task.active_dataset = dataset

        # Import was successful
        os.remove(os.path.join(self.path, ".import_error"))

        logger.info("Task parameters loaded.")

        return task

    def contest_has_changed(self):
        """See docstring in class ContestLoader."""
        name = os.path.split(self.path)[1]
        contest_yaml = os.path.join(self.path, "contest.yaml")

        if not os.path.exists(contest_yaml):
            logger.critical("File missing: \"contest.yaml\"")
            sys.exit(1)

        # If there is no .itime file, we assume that the contest has changed
        if not os.path.exists(os.path.join(self.path, ".itime_contest")):
            return True

        itime = getmtime(os.path.join(self.path, ".itime_contest"))

        # Check if contest.yaml has changed
        if getmtime(contest_yaml) > itime:
            return True

        if os.path.exists(os.path.join(self.path, ".import_error_contest")):
            logger.warning("Last attempt to import contest %s failed, I'm not "
                           "trying again. After fixing the error, delete the "
                           "file .import_error_contest", name)
            sys.exit(1)

        return False

    def user_has_changed(self):
        """See docstring in class UserLoader."""
        # This works as users are kept inside contest.yaml, so changing
        # them alters the last modified time of contest.yaml.
        # TODO Improve this.
        return self.contest_has_changed()

    def team_has_changed(self):
        """See docstring in class TeamLoader."""
        # This works as teams are kept inside contest.yaml, so changing
        # them alters the last modified time of contest.yaml.
        # TODO Improve this.
        return self.contest_has_changed()

    def task_has_changed(self):
        """See docstring in class TaskLoader."""
        name = os.path.split(self.path)[1]

        if (not os.path.exists(os.path.join(self.path, "task.yaml"))) and \
           (not os.path.exists(os.path.join(self.path, "..", name + ".yaml"))):
            logger.critical("File missing: \"task.yaml\"")
            sys.exit(1)

        # We first look for the yaml file inside the task folder,
        # and eventually fallback to a yaml file in its parent folder.
        try:
            conf = load_yaml_from_path(os.path.join(self.path, "task.yaml"))
        except OSError:
            conf = load_yaml_from_path(
                os.path.join(self.path, "..", name + ".yaml"))

        # If there is no .itime file, we assume that the task has changed
        if not os.path.exists(os.path.join(self.path, ".itime")):
            return True

        itime = getmtime(os.path.join(self.path, ".itime"))

        # Generate a task's list of files
        # Testcases
        files = []
        for filename in os.listdir(os.path.join(self.path, "input")):
            files.append(os.path.join(self.path, "input", filename))

        for filename in os.listdir(os.path.join(self.path, "output")):
            files.append(os.path.join(self.path, "output", filename))

        # Attachments
        if os.path.exists(os.path.join(self.path, "att")):
            for filename in os.listdir(os.path.join(self.path, "att")):
                files.append(os.path.join(self.path, "att", filename))

        files += glob.glob("%s/templates/template*" % self.path)

        # Score file
        files.append(os.path.join(self.path, "gen", "GEN"))

        # Statement
        files += glob.glob("%s/statement/statement.*.pdf" % self.path)

        # Managers
        files.append(os.path.join(self.path, "check", "checker"))
        files.append(os.path.join(self.path, "cor", "correttore"))
        files.append(os.path.join(self.path, "check", "manager"))
        files.append(os.path.join(self.path, "cor", "manager"))
        files.append(os.path.join(self.path, "check", "batchmanager"))
        if not conf.get('output_only', False) and \
                os.path.isdir(os.path.join(self.path, "solution")):
            for lang in LANGUAGES:
                files.append(os.path.join(
                    self.path, "solution", "grader%s" % lang.source_extension))
            for other_filename in os.listdir(os.path.join(self.path, "solution")):
                if any(other_filename.endswith(header)
                       for header in HEADER_EXTS):
                    files.append(
                        os.path.join(self.path, "solution", other_filename))

        # Yaml
        files.append(os.path.join(self.path, "task.yaml"))
        files.append(os.path.join(self.path, "..", name + ".yaml"))

        # Check is any of the files have changed
        for fname in files:
            if os.path.exists(fname):
                if getmtime(fname) > itime:
                    return True

        # Check if checkers need to be rebuilt
        if os.path.exists(os.path.join(self.path, "check", "Makefile")):
            res = subprocess.run(["make", "--question"], cwd=os.path.join(self.path, "check"))
            if res.returncode == 1:
                return True
            if res.returncode != 0:
                logger.error("Error occurred when building checkers")
                sys.exit(1)

        if os.path.exists(os.path.join(self.path, ".import_error")):
            logger.warning("Last attempt to import task %s failed, I'm not "
                           "trying again. After fixing the error, delete the "
                           "file .import_error", name)
            sys.exit(1)

        return False
