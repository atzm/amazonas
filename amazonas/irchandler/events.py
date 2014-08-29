# -*- coding: utf-8 -*-

import amazonas.util
import amazonas.ircplugin


@amazonas.ircplugin.event('join')
def oper(conn, event):
    if not amazonas.util.config_enabled('event:join:oper'):
        return
    if event.source.nick == conn.get_nickname():
        return
    conn.mode(event.target, '+o %s' % event.source.nick)
