# -*- coding: utf-8 -*-

import re
import logging

from .. import util
from .. import ircplugin


@ircplugin.action('null')
def null(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    pass


@ircplugin.action('oper')
def oper(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    if not replyto or not msgfrom:
        logging.error('cannot exec with "replyto:%s" and "msgfrom:%s"',
                      replyto, msgfrom)
        return
    conn.mode(replyto, '+o %s' % msgfrom)


@ircplugin.action('disoper')
def disoper(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    if not replyto or not msgfrom:
        logging.error('cannot exec with "replyto:%s" and "msgfrom:%s"',
                      replyto, msgfrom)
        return
    conn.mode(replyto, '-o %s' % msgfrom)


@ircplugin.action('learn')
def learn(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    if not msg:
        return

    replace_nick = conf.get('replace_nick', '')
    if replace_nick and msgfrom:
        msg = re.sub(replace_nick, msgfrom, msg)

    client = util.HTTPClient(str(conf['server']), int(conf['port']))
    path = str('/'.join(('/v0.1', conf['instance'])))

    code, _ = client.put(path, {'text': [msg]})
    if code == 204:
        logging.info('learning success: %s', msg)
    else:
        logging.warn('learning failed: %s', msg)


@ircplugin.action('talk')
def talk(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    client = util.HTTPClient(str(conf['server']), int(conf['port']))
    path = str('/'.join(('/v0.1', conf['instance'])))

    code, body = client.get(path)
    if code == 200:
        conn.notice(replyto, body['text'])
        logging.info('talked: [%s] %s', replyto, body['text'])
    else:
        logging.warn('failed to get a text: %d', code)
