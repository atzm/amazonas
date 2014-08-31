# -*- coding: utf-8 -*-

import random
import logging

from .. import util
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


@ircplugin.command('suggest')
def suggest(ircbot, conn, event, msgfrom, replyto, *args):
    locale = config.get('command:suggest', 'locale') or 'en'
    limit = config.getint('command:suggest', 'limit') or 1
    randomize = config.getboolean('command:suggest', 'randomize')
    notfound = config.get('command:suggest', 'notfound') or 'not found'

    client = util.HTTPClient('www.google.com', 443, True)
    code, body = client.get('/complete/search', hl=locale,
                            client='firefox', q=' '.join(args))

    if code != 200:
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
