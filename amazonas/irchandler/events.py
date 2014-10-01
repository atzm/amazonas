# -*- coding: utf-8 -*-

from .. import ircplugin


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
    ircbot.send_message(conn, event.target, 'event:join:message')
