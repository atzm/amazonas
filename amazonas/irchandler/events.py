# -*- coding: utf-8 -*-

from .. import config
from .. import ircplugin


@ircplugin.event('join')
def oper(conn, event):
    if not config.enabled('event:join:oper'):
        return
    if event.source.nick == conn.get_nickname():
        return
    conn.mode(event.target, '+o %s' % event.source.nick)
