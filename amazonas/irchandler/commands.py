# -*- coding: utf-8 -*-

import random
import logging

from .. import util
from .. import config
from .. import ircplugin


@ircplugin.command('help')
def help(ircbot, conn, event, msgfrom, replyto, *args):
    '''[<command>]
    Display help message.
    '''
    cmdlist = []
    for name, command in ircplugin.itercommands():
        if args and args[0] != name:
            continue
        if not ircbot.isenabled(':'.join(('command', name)), msgfrom):
            continue
        cmdlist.append((name, command))

    for line in util.formathelp(cmdlist).splitlines():
        conn.notice(replyto, line.rstrip())

    return {}


@ircplugin.command('version')
def version(ircbot, conn, event, msgfrom, replyto, *args):
    '''(no arguments required)
    Display version information.
    '''
    conn.notice(replyto, 'amazonas/0.0.1')
    return {}


@ircplugin.command('reload')
def reload(ircbot, conn, event, msgfrom, replyto, *args):
    '''(no arguments required)
    Reload configuration.
    '''
    config.reload()
    logging.info('[reload] config reloaded')
    return {}


@ircplugin.command('activate')
def activate(ircbot, conn, event, msgfrom, replyto, *args):
    '''(no arguments required)
    Enable any actions.
    '''
    ircbot.action_active = True
    logging.info('[activate] activated')
    return {}


@ircplugin.command('deactivate')
def deactivate(ircbot, conn, event, msgfrom, replyto, *args):
    '''(no arguments required)
    Disable any actions.
    '''
    ircbot.action_active = False
    logging.info('[deactivate] deactivated')
    return {}


@ircplugin.command('suggest')
def suggest(ircbot, conn, event, msgfrom, replyto, *args):
    '''<val1> [<val2> [...]]
    Display suggestion(s) from specified values.
    '''
    locale = config.get('command:suggest', 'locale') or 'en'
    limit = config.getint('command:suggest', 'limit') or 1
    nr_retry = config.getint('command:suggest', 'nr_retry')
    randomize = config.getboolean('command:suggest', 'randomize')
    notfound = config.get('command:suggest', 'notfound') or 'not found'

    if limit < 1:
        logging.warn('[suggest] detected limit < 1')
        limit = 1
    if nr_retry < 0:
        logging.warn('[suggest] detected nr_retry < 0')
        nr_retry = 0

    result = util.gcomplete(' '.join(args), locale, nr_retry)
    if not result:
        conn.notice(replyto, notfound)
        return None

    if randomize:
        random.shuffle(result)

    for text in result[:limit]:
        conn.notice(replyto, text)

    return {}
