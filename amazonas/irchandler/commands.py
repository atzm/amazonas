# -*- coding: utf-8 -*-

import random
import logging

from .. import util
from .. import config
from .. import ircplugin


@ircplugin.command('help')
def help(ircbot, conn, event, data, *args):
    '''[<command>]
    Display help message.
    '''
    cmdlist = []
    for name, command in ircplugin.itercommands():
        sect = ':'.join(('command', name))
        if args and args[0] != name:
            continue
        if not ircbot.isenabled(sect, data.copy()):
            continue
        cmdlist.append((name, command))

    for line in util.formathelp(cmdlist).splitlines():
        line = line.rstrip()
        if not line:
            continue
        conn.notice(data['target'], line)
        logging.info('[help] [%s] %s> %s', data['target'],
                     conn.get_nickname(), line)

    return {}


@ircplugin.command('version')
def version(ircbot, conn, event, data, *args):
    '''(no arguments required)
    Display version information.
    '''
    line = 'amazonas/0.0.1'
    conn.notice(data['target'], line)
    logging.info('[version] [%s] %s> %s', data['target'],
                 conn.get_nickname(), line)
    return {}


@ircplugin.command('reload')
def reload(ircbot, conn, event, data, *args):
    '''(no arguments required)
    Reload configuration.
    '''
    ircbot.unregister_schedule()
    config.reload()
    ircbot.register_schedule()
    logging.info('[reload] config reloaded')
    return {}


@ircplugin.command('activate')
def activate(ircbot, conn, event, data, *args):
    '''(no arguments required)
    Enable any actions.
    '''
    ircbot.action_active = True
    logging.info('[activate] activated')
    return {}


@ircplugin.command('deactivate')
def deactivate(ircbot, conn, event, data, *args):
    '''(no arguments required)
    Disable any actions.
    '''
    ircbot.action_active = False
    logging.info('[deactivate] deactivated')
    return {}


@ircplugin.command('suggest')
def suggest(ircbot, conn, event, data, *args):
    '''<val1> [<val2> [...]]
    Display suggestion(s) from specified values.
    '''
    locale = config.get('command:suggest', 'locale') or 'en'
    limit = config.getint('command:suggest', 'limit') or 1
    nr_retry = config.getint('command:suggest', 'nr_retry')
    randomize = config.getboolean('command:suggest', 'randomize')
    notfound = config.get('command:suggest', 'notfound') or 'not found'

    gclient = util.http.GoogleClient()
    result = gclient.complete(' '.join(args), locale, nr_retry)
    if not result:
        conn.notice(data['target'], notfound)
        logging.info('[suggest] [%s] %s> %s', data['target'],
                     conn.get_nickname(), notfound)
        return None

    if randomize:
        random.shuffle(result)

    for text in result[:limit]:
        conn.notice(data['target'], text)
        logging.info('[suggest] [%s] %s> %s', data['target'],
                     conn.get_nickname(), text)

    return {}
