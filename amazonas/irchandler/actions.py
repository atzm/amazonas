# -*- coding: utf-8 -*-

import re
import time
import random
import logging

from .. import util
from .. import ircplugin


@ircplugin.action('null')
def null(ircbot, conf, conn, event, msgfrom, replyto, msg):
    return {}


@ircplugin.action('log')
def log(ircbot, conf, conn, event, msgfrom, replyto, msg):
    func = getattr(logging, conf.get('level', 'info'), logging.info)
    func('[log]  [%s] %s> %s', replyto, msgfrom, msg)
    return {}


@ircplugin.action('oper')
def oper(ircbot, conf, conn, event, msgfrom, replyto, msg):
    if not replyto or not msgfrom:
        logging.error('[oper] cannot exec with "replyto:%s", "msgfrom:%s"',
                      replyto, msgfrom)
        return None
    conn.mode(replyto, '+o %s' % msgfrom)
    return {}


@ircplugin.action('disoper')
def disoper(ircbot, conf, conn, event, msgfrom, replyto, msg):
    if not replyto or not msgfrom:
        logging.error('[disoper] cannot exec with "replyto:%s", "msgfrom:%s"',
                      replyto, msgfrom)
        return None
    conn.mode(replyto, '-o %s' % msgfrom)
    return {}


@ircplugin.action('learn')
def learn(ircbot, conf, conn, event, msgfrom, replyto, msg):
    if not msg:
        logging.error('[learn] cannot exec without any messages')
        return None

    replace_nick = conf.get('replace_nick', '')
    if replace_nick and msgfrom:
        msg = re.sub(replace_nick, msgfrom, msg)

    client = util.http.APIClientV01(conf['server'], conf['port'])
    if client.learn(conf['instance'], [msg], int(conf.get('nr_retry', 0))):
        return {}

    logging.warn('[learn] failed to learn "%s"', msg)
    return None


@ircplugin.action('talk')
def talk(ircbot, conf, conn, event, msgfrom, replyto, msg):
    client = util.http.APIClientV01(conf['server'], conf['port'])
    score, text = client.generate(conf['instance'],
                                  int(conf.get('nr_retry', 0)))
    if None in (score, text):
        logging.warn('[talk] failed to generate text')
        return None

    for line in text.splitlines():
        if not line:
            continue
        conn.notice(replyto, line)
        logging.info('[talk] [%s] %s> %s', replyto, conn.get_nickname(), line)

    return {}


@ircplugin.action('suggest')
def suggest(ircbot, conf, conn, event, msgfrom, replyto, msg):
    nr_retry = int(conf.get('nr_retry', 0))
    client = util.http.APIClientV01(conf['server'], conf['port'])
    keys = client.recent_entries(conf['instance'], nr_retry)
    if not keys:
        logging.warn('[suggest] failed to get recent entries')
        return None

    key = random.choice(keys)
    gclient = util.http.GoogleClient()
    result = gclient.complete(key, conf.get('locale', 'en'), nr_retry)
    if not result:
        logging.warn('[suggest] failed to complete with "%s"', key)
        return None

    return {'suggested': random.choice(result)}


@ircplugin.action('learn-jlyrics')
def learn_jlyrics(ircbot, conf, conn, event, msgfrom, replyto, msg):
    nr_retry = int(conf.get('nr_retry', 0))
    client = util.http.APIClientV01(conf['server'], conf['port'])
    keys = client.recent_entries(conf['instance'], nr_retry)
    if not keys:
        logging.warn('[learn-jlyrics] failed to get recent entries')
        return None

    key = random.choice(keys)
    for title, title_id, artist, artist_id in util.jlyrics.search(lyrics=key):
        time.sleep(random.randint(1, 3))  # XXX: reduce server load
        lyrics = util.jlyrics.get(artist_id, title_id)
        break
    else:
        logging.warn('[learn-jlyrics] lyrics not found with "%s"', key)
        return None

    lines = [line.strip() for line in lyrics.splitlines() if line.strip()]
    if client.learn(conf['instance'], lines, nr_retry):
        logging.info('[learn-jlyrics] learned with "%s"', key)
        return {}

    logging.warn('[learn-jlyrics] failed to learn with "%s"', key)
    return None
