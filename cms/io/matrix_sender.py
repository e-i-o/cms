#!/usr/bin/env python3

"""
Class that handles sending messages to a Matrix channel.
(Doesn't work in end-to-end encrypted rooms. Probably.)
"""

import logging
import gevent
import requests
import urllib.parse
import random
import string

from cms import config

logger = logging.getLogger(__name__)

def send_message_internal(token, room_id, homeserver, text):
    room_id = urllib.parse.quote(room_id, safe='')
    random_string = ''.join(random.choices(string.ascii_letters, k=20))
    data = {
        "msgtype": "m.text",
        "body": text,
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with requests.put(f"{homeserver}/_matrix/client/r0/rooms/{room_id}/send/m.room.message/{random_string}", json=data, headers=headers) as r:
            r.raise_for_status()
    except Exception as e:
        logger.error("Error when sending matrix notification:\n%s", e)
        return
    logger.info("Successfully sent matrix notification.")

def send_matrix_message(text: str):
    token = config.matrix_bot_token
    room_id = config.matrix_bot_room_id
    homeserver = config.matrix_bot_homeserver
    if token is None and room_id is None and homeserver is None:
        # No matrix room configured.
        return
    if token is None or room_id is None or homeserver is None:
        logger.warning("Matrix notifier settings missing, not sending message.")
        return
    gevent.spawn(send_message_internal, token, room_id, homeserver, text)


