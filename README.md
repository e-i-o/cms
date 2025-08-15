Contest Management System
=========================

This is a fork of CMS as used in Estonian informatics olympiads. We periodically rebase all of our patches on top of the upstream repo. Each commit on this branch should be one "change". Fixup commits must clearly indicate which change they are meant to be a part of.

`eio` is the development branch, any pushes will automatically build the `ghcr.io/e-i-o/cms:test` docker image. `eio-prod` is the production branch, any pushes will build the `ghcr.io/e-i-o/cms:prod` docker image.

Making changes: Preferably fix the tests if they fail (use docker/cms-test.sh). The docker image should get pushed even when tests fail though.

When changing translatable strings:

1. Edit the string in CMS code.
2. Run `./setup.py extract_messages`.
3. Undo the unnecessary modifications to the file header of cms/locale/cms.pot (this should only be the generation date changing). This prevents merge conflicts when rebasing later.
4. Run `./setup.py update_catalog -l et` and `./setup.py update_catalog -l ru`.
5. Again, undo the changes to the file headers (and possibly footers) of the .po files.
6. Add your translations to the .po files.

When only changing the translations, not the source strings, it's preferable to [submit the changes upstream](https://hosted.weblate.org/engage/cms/) instead if possible.

Rebase procedure:

1. Make a new tag from the `eio` branch, named something like `eio-2025-02` (for keeping history).
2. Squash any fixup commits into their respective change commits.
3. Rebase on top of upstream main, remove any now-unnecessary patches. (Depending on circumstances, it might be easier to cherry-pick all patches that are worth keeping instead.)
4. Force push :)

Original readme follows:

Homepage: <http://cms-dev.github.io/>

[![Build Status](https://github.com/cms-dev/cms/actions/workflows/main.yml/badge.svg)](https://github.com/cms-dev/cms/actions)
[![Codecov](https://codecov.io/gh/cms-dev/cms/branch/main/graph/badge.svg)](https://codecov.io/gh/cms-dev/cms)
[![Get support on Telegram](https://img.shields.io/badge/Questions%3F-Join%20the%20Telegram%20group!-%2326A5E4?style=flat&logo=telegram)](https://t.me/contestms)
[![Translation status](https://hosted.weblate.org/widget/cms/svg-badge.svg)](https://hosted.weblate.org/engage/cms/)

[🌍 Help translate CMS in your language using Weblate!](https://hosted.weblate.org/engage/cms/)

Introduction
------------

CMS, or Contest Management System, is a distributed system for running
and (to some extent) organizing a programming contest.

CMS has been designed to be general and to handle many different types
of contests, tasks, scorings, etc. Nonetheless, CMS has been
explicitly build to be used in the 2012 International Olympiad in
Informatics, held in September 2012 in Italy.


Download
--------

**For end-users it's best to download the latest stable version of CMS,
which can be found already packaged at <http://cms-dev.github.io/>.**

This git repository, which contains the development version in its
main branch, is intended for developers and everyone interested in
contributing or just curious to see how the code works and wanting to
hack on it.


Support
-------

To learn how to install and use CMS, please read the **documentation**,
available at <https://cms.readthedocs.org/>.

If you have questions or need help troubleshooting some problem, contact us in
the **chat** on [Telegram](https://t.me/contestms), or write on the **support
mailing list** <contestms-support@googlegroups.com>, where no registration is
required (you can see the archives on [Google
Groups](https://groups.google.com/forum/#!forum/contestms-support)).

To help with the troubleshooting, you can upload on some online pastebin the
relevant **log files**, that you can find in `/var/local/log/cms/`.

If you encountered a bug, please file an
[issue](https://github.com/cms-dev/cms/issues) on **GitHub** following the
instructions in the issue template.

**Please don't file issues to ask for help**, we are happy to help on the
mailing list or on Telegram, and it is more likely somebody will answer your
query sooner.

You can subscribe to <contestms-announce@googlegroups.com> to receive
**announcements** of new releases and other important news. Register on
[Google Groups](https://groups.google.com/forum/#!forum/contestms-announce).

For **development** queries, you can write to
<contestms-discuss@googlegroups.com> and as before subscribe or see the
archives on
[Google Groups](https://groups.google.com/forum/#!forum/contestms-discuss).



Testimonials
------------

CMS has been used in several official and unofficial contests. Please
find an updated list at <http://cms-dev.github.io/testimonials.html>.

If you used CMS for a contest, selection, or a similar event, and want
to publicize this information, we would be more than happy to hear
from you and add it to that list.
