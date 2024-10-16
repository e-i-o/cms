#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2013 Luca Wehrstedt <luca.wehrstedt@gmail.com>
# Copyright © 2014 Stefano Maggiolo <s.maggiolo@gmail.com>
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

# Define what this package will provide.

__all__ = [
    # rpc
    "RPCError", "rpc_method", "RemoteServiceServer", "RemoteServiceClient",
    # service
    "Service",
    # triggeredservice
    "Executor", "TriggeredService",
    # priorityqueue
    "FakeQueueItem", "PriorityQueue", "QueueEntry", "QueueItem",
    # web_rpc
    "RPCMiddleware",
    # web_service
    "WebService",
    # matrix_sender
    "send_matrix_message",
    ]


# Instantiate or import these objects.

from .PsycoGevent import make_psycopg_green
from .priorityqueue import FakeQueueItem, PriorityQueue, QueueEntry, QueueItem
from .rpc import RPCError, rpc_method, RemoteServiceServer, RemoteServiceClient
from .service import Service
from .triggeredservice import Executor, TriggeredService
from .web_rpc import RPCMiddleware
from .web_service import WebService
from .matrix_sender import send_matrix_message


# Fix psycopg in order to support gevent greenlets.
make_psycopg_green()
