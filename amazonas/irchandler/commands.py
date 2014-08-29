# -*- coding: utf-8 -*-

import logging

from .. import config
from .. import ircplugin


@ircplugin.command('version')
def version(ircbot, conn, event, msgfrom, replyto, *args):
    conn.notice(replyto, 'amazonas/0.0.1')


@ircplugin.command('reload')
def reload(ircbot, conn, event, msgfrom, replyto, *args):
    config.reload()
    logging.info('config reloaded')


@ircplugin.command('activate')
def activate(ircbot, conn, event, msgfrom, replyto, *args):
    ircbot.action_active = True
    logging.info('activated')


@ircplugin.command('deactivate')
def deactivate(ircbot, conn, event, msgfrom, replyto, *args):
    ircbot.action_active = False
    logging.info('deactivated')
