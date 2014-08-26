# -*- coding: utf-8 -*-

import amazonas.config
import amazonas.ircplugin


@amazonas.ircplugin.command('version')
def version(ircbot, conn, event, msgfrom, replyto, *args):
    conn.notice(replyto, 'amazonas/0.0.1')


@amazonas.ircplugin.command('reload')
def reload(ircbot, conn, event, msgfrom, replyto, *args):
    amazonas.config.reload()
    conn.notice(replyto, 'config reloaded')
