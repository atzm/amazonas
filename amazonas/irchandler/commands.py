# -*- coding: utf-8 -*-

import logging
import amazonas.config
import amazonas.ircplugin


@amazonas.ircplugin.command('version')
def version(ircbot, conn, event, msgfrom, replyto, *args):
    conn.notice(replyto, 'amazonas/0.0.1')


@amazonas.ircplugin.command('reload')
def reload(ircbot, conn, event, msgfrom, replyto, *args):
    amazonas.config.reload()
    logging.info('config reloaded')


@amazonas.ircplugin.command('activate')
def activate(ircbot, conn, event, msgfrom, replyto, *args):
    ircbot.action_active = True
    logging.info('activated')


@amazonas.ircplugin.command('deactivate')
def deactivate(ircbot, conn, event, msgfrom, replyto, *args):
    ircbot.action_active = False
    logging.info('deactivated')
