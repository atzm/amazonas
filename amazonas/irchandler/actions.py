# -*- coding: utf-8 -*-

import re
import random
import logging

from .. import util
from .. import ircplugin


@ircplugin.action('null')
def null(ircbot, conf, conn, event, msgfrom, replyto, msg):
    pass


@ircplugin.action('log')
def log(ircbot, conf, conn, event, msgfrom, replyto, msg):
    func = getattr(logging, conf.get('level', 'info'), logging.info)
    func('[log]  [%s] %s> %s', replyto, msgfrom, msg)


@ircplugin.action('oper')
def oper(ircbot, conf, conn, event, msgfrom, replyto, msg):
    if not replyto or not msgfrom:
        logging.error('[oper] cannot exec with "replyto:%s", "msgfrom:%s"',
                      replyto, msgfrom)
        return
    conn.mode(replyto, '+o %s' % msgfrom)


@ircplugin.action('disoper')
def disoper(ircbot, conf, conn, event, msgfrom, replyto, msg):
    if not replyto or not msgfrom:
        logging.error('[disoper] cannot exec with "replyto:%s", "msgfrom:%s"',
                      replyto, msgfrom)
        return
    conn.mode(replyto, '-o %s' % msgfrom)


@ircplugin.action('learn')
def learn(ircbot, conf, conn, event, msgfrom, replyto, msg):
    if not msg:
        logging.error('[learn] cannot exec without any messages')
        return

    replace_nick = conf.get('replace_nick', '')
    if replace_nick and msgfrom:
        msg = re.sub(replace_nick, msgfrom, msg)

    client = util.HTTPClient(conf['server'], conf['port'])
    path = '/'.join(('/v0.1', conf['instance']))
    nr_retry = int(conf.get('nr_retry', 0))

    if nr_retry < 0:
        logging.warn('[learn] detected nr_retry < 0')
        nr_retry = 0

    for x in xrange(1, nr_retry + 2):
        code, _ = client.put(path, {'text': [msg]})

        if code == 204:
            return

        logging.warn('[learn] [#%d] failed with %d / "%s"', x, code, msg)


@ircplugin.action('talk')
def talk(ircbot, conf, conn, event, msgfrom, replyto, msg):
    client = util.HTTPClient(conf['server'], conf['port'])
    path = '/'.join(('/v0.1', conf['instance']))
    nr_retry = int(conf.get('nr_retry', 0))

    if nr_retry < 0:
        logging.warn('[talk] detected nr_retry < 0')
        nr_retry = 0

    for x in xrange(1, nr_retry + 2):
        code, body = client.get(path)

        if code == 200:
            conn.notice(replyto, body['text'])
            logging.info('[talk] [%s] %s> %s',
                         replyto, conn.get_nickname(), body['text'])
            return

        logging.warn('[talk] [#%d] failed with %d', x, code)


@ircplugin.action('suggest')
def suggest(ircbot, conf, conn, event, msgfrom, replyto, msg):
    locale = conf.get('locale', 'en')
    nr_retry = int(conf.get('nr_retry', 0))

    if nr_retry < 0:
        logging.warn('[suggest] detected nr_retry < 0')
        nr_retry = 0

    client = util.HTTPClient(conf['server'], conf['port'])
    path = '/'.join(('/v0.1', conf['instance'], 'recent-entrypoints'))

    for x in xrange(1, nr_retry + 2):
        code, body = client.get(path)
        if code == 200:
            break
        logging.warn('[suggest] [#%d] failed with %d', x, code)
    else:
        return
    if not body['keys']:
        return

    result = util.gcomplete(random.choice(body['keys']), locale, nr_retry)
    if not result:
        return

    return {'suggested': random.choice(result)}
