# -*- coding: utf-8 -*-

import logging

from .. import config
from .. import ircplugin


@ircplugin.event('all')
def log(ircbot, conn, event):
    source = getattr(event.source, 'nick', str(event.source))
    level = config.get('event:all:log', 'level')
    fmt = config.get('event:all:log', 'format')
    ignore = config.getlist('event:all:log', 'ignore')

    if not ircbot.isenabled('event:all:log', source):
        return

    if event.type in ignore:
        return

    data = {
        'type':    event.type,
        'target':  event.target,
        'source':  source,
        'message': ' '.join(event.arguments),
    }

    fmt = fmt.encode('raw_unicode_escape').decode('unicode_escape')
    getattr(logging, level, logging.info)(fmt % data)


@ircplugin.event('join')
def oper(ircbot, conn, event):
    if not ircbot.isenabled('event:join:oper', event.source.nick):
        return
    if event.source.nick == conn.get_nickname():
        return
    conn.mode(event.target, '+o %s' % event.source.nick)


@ircplugin.event('join')
def message(ircbot, conn, event):
    if not ircbot.isenabled('event:join:message'):
        return
    if event.source.nick != conn.get_nickname():
        return
    ircbot.send_message(conn, 'event:join:message', {'target': event.target})
