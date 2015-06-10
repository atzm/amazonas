# -*- coding: utf-8 -*-

import re
import time
import random
import logging

from .. import util
from .. import ircplugin


@ircplugin.action('null')
def null(ircbot, conf, conn, event, data):
    return {}


@ircplugin.action('oper')
def oper(ircbot, conf, conn, event, data):
    if 'target' not in data or 'source' not in data:
        logging.error('[oper] cannot exec without "target" and "source"')
        return None
    conn.mode(data['target'], '+o %s' % data['source'])
    return {}


@ircplugin.action('disoper')
def disoper(ircbot, conf, conn, event, data):
    if 'target' not in data or 'source' not in data:
        logging.error('[disoper] cannot exec without "target" and "source"')
        return None
    conn.mode(data['target'], '-o %s' % data['source'])
    return {}


@ircplugin.action('replace')
def replace(ircbot, conf, conn, event, data):
    if 'message' not in data:
        logging.error('[replace] cannot exec without any messages')
        return None

    regex = conf['regex']
    replace = conf['replace'] % data

    # replace plugin manipulates the message itself,
    # so it affects pattern matching of next actions.
    return {'message': re.sub(regex, replace, data['message'])}


@ircplugin.action('learn')
def learn(ircbot, conf, conn, event, data):
    if 'message' not in data:
        logging.error('[learn] cannot exec without any messages')
        return None

    # learn plugin manipulates the message temporarily,
    # so it does not affect any other actions.
    message = data['message']
    replace_regex = conf.get('replace_regex')
    replace_with = conf.get('replace_with')
    if replace_regex and replace_with is not None:
        replace_with = replace_with % data
        message = re.sub(replace_regex, replace_with, message)

    retry = int(conf.get('nr_retry', 0))
    client = util.http.APIClientV01(conf['server'], conf['port'])
    if client.learn(conf['instance'], [message], retry):
        return {}

    logging.warn('[learn] failed to learn "%s"', message)
    return None


@ircplugin.action('talk')
def talk(ircbot, conf, conn, event, data):
    client = util.http.APIClientV01(conf['server'], conf['port'])
    score, text = client.generate(conf['instance'],
                                  int(conf.get('nr_retry', 0)))
    if None in (score, text):
        logging.warn('[talk] failed to generate text')
        return None

    for line in text.splitlines():
        if not line:
            continue
        conn.notice(data['target'], line)
        logging.info('[talk] [%s] %s> %s',
                     data['target'], conn.get_nickname(), line)

    return {}


@ircplugin.action('suggest')
def suggest(ircbot, conf, conn, event, data):
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


@ircplugin.action('html')
def html(ircbot, conf, conn, event, data):
    if 'message' not in data:
        logging.error('[html] cannot exec without any messages')
        return None

    url = data['message'].split()[0]
    timeout = float(conf.get('timeout', 2.0))
    xpath = conf['xpath']
    content = util.http.HTML(url, timeout).getcontent(xpath)

    if content:
        return content

    logging.warn('[html] failed to get %s on %s', xpath, url)
    return None


@ircplugin.action('learn-jlyrics')
def learn_jlyrics(ircbot, conf, conn, event, data):
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
