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
    for name, cmds in ircplugin.itercommands():
        if args and args[0] != name:
            continue
        if not config.enabled(':'.join(('command', name))):
            continue
        for cmd in cmds:
            cmdlist.append((name, cmd))

    for line in util.formathelp(cmdlist).splitlines():
        conn.notice(replyto, line.rstrip())


@ircplugin.command('version')
def version(ircbot, conn, event, msgfrom, replyto, *args):
    '''(no arguments required)
    Display version information.
    '''
    conn.notice(replyto, 'amazonas/0.0.1')


@ircplugin.command('reload')
def reload(ircbot, conn, event, msgfrom, replyto, *args):
    '''(no arguments required)
    Reload configuration.
    '''
    config.reload()
    logging.info('[reload] config reloaded')


@ircplugin.command('activate')
def activate(ircbot, conn, event, msgfrom, replyto, *args):
    '''(no arguments required)
    Enable any actions.
    '''
    ircbot.action_active = True
    logging.info('[activate] activated')


@ircplugin.command('deactivate')
def deactivate(ircbot, conn, event, msgfrom, replyto, *args):
    '''(no arguments required)
    Disable any actions.
    '''
    ircbot.action_active = False
    logging.info('[deactivate] deactivated')


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

    client = util.HTTPClient('www.google.com', 443, True)

    if limit < 1:
        logging.warn('[suggest] detected limit < 1')
        limit = 1
    if nr_retry < 0:
        logging.warn('[suggest] detected nr_retry < 0')
        nr_retry = 0

    for x in xrange(1, nr_retry + 2):
        code, body = client.get('/complete/search', hl=locale,
                                client='firefox', q=' '.join(args))
        if code == 200:
            break
    else:
        return conn.notice(replyto, notfound)

    if type(body) is not list:
        return conn.notice(replyto, notfound)
    if len(body) < 2:
        return conn.notice(replyto, notfound)
    if type(body[1]) is not list:
        return conn.notice(replyto, notfound)
    if not body[1]:
        return conn.notice(replyto, notfound)

    if randomize:
        random.shuffle(body[1])

    for text in body[1][:limit]:
        conn.notice(replyto, text)
