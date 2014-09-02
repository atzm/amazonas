# -*- coding: utf-8 -*-

import re
import logging

from .. import util
from .. import ircplugin


@ircplugin.action('null')
def null(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    pass


@ircplugin.action('log')
def log(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    func = getattr(logging, conf.get('level', 'info'), logging.info)
    func('[log]  [%s] %s> %s', replyto, msgfrom, msg)


@ircplugin.action('oper')
def oper(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    if not replyto or not msgfrom:
        logging.error('[oper] cannot exec with "replyto:%s", "msgfrom:%s"',
                      replyto, msgfrom)
        return
    conn.mode(replyto, '+o %s' % msgfrom)


@ircplugin.action('disoper')
def disoper(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    if not replyto or not msgfrom:
        logging.error('[disoper] cannot exec with "replyto:%s", "msgfrom:%s"',
                      replyto, msgfrom)
        return
    conn.mode(replyto, '-o %s' % msgfrom)


@ircplugin.action('learn')
def learn(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    if not msg:
        logging.error('[learn] cannot exec without any messages')
        return

    replace_nick = conf.get('replace_nick', '')
    if replace_nick and msgfrom:
        msg = re.sub(replace_nick, msgfrom, msg)

    client = util.HTTPClient(conf['server'], conf['port'])
    path = '/'.join(('/v0.1', conf['instance']))

    code, _ = client.put(path, {'text': [msg]})
    if code != 204:
        logging.warn('[learn] failed with %d / "%s"', code, msg)


@ircplugin.action('talk')
def talk(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    client = util.HTTPClient(conf['server'], conf['port'])
    path = '/'.join(('/v0.1', conf['instance']))

    code, body = client.get(path)
    if code == 200:
        conn.notice(replyto, body['text'])
        logging.info('[talk] [%s] %s> %s',
                     replyto, conn.get_nickname(), body['text'])
    else:
        logging.warn('[talk] failed with %d', code)
