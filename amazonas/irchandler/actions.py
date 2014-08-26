# -*- coding: utf-8 -*-

import re
import logging

import amazonas.util
import amazonas.config
import amazonas.ircplugin


@amazonas.ircplugin.action('null')
def null(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    pass


@amazonas.ircplugin.action('oper')
def oper(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    if not replyto or not msgfrom:
        logging.warn('cannot exec with "replyto:%s" and "msgfrom:%s"',
                     replyto, msgfrom)
        return
    conn.mode(replyto, '+o %s' % msgfrom)


@amazonas.ircplugin.action('learn')
def learn(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    if not msg:
        return

    replace_nick = conf.get('replace_nick', '')
    if replace_nick and msgfrom:
        msg = re.sub(replace_nick, msgfrom, msg)

    client = amazonas.util.HTTPClient(str(conf['server']), int(conf['port']))
    path = str('/'.join(('/v0.1', conf['instance'])))

    code, _ = client.put(path, {'text': [msg]})
    if code == 204:
        logging.info('learning success: %s', msg)
    else:
        logging.warn('learning failed: %s', msg)


@amazonas.ircplugin.action('talk')
def talk(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    client = amazonas.util.HTTPClient(str(conf['server']), int(conf['port']))
    path = str('/'.join(('/v0.1', conf['instance'])))

    code, body = client.get(path)
    text = body.get('text', None)

    if code == 200 and text is not None:
        conn.notice(replyto, text)
        logging.info('talked: [%s] %s', replyto, text)
    else:
        logging.warn('failed to get a text: %d', code)


@amazonas.ircplugin.action('activate')
def activate(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    logging.info('not implemented: activate')


@amazonas.ircplugin.action('deactivate')
def deactivate(ircbot, match, conf, conn, event, msgfrom, replyto, msg):
    logging.info('not implemented: deactivate')
