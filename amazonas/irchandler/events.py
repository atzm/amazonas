# -*- coding: utf-8 -*-

import amazonas.config
import amazonas.ircplugin


@amazonas.ircplugin.event('join')
def oper(conn, event):
    if not amazonas.config.getboolean('event:join:oper', 'enable'):
        return
    if event.source.nick == conn.get_nickname():
        return

    conn.mode(event.target, '+o %s' % event.source.nick)
