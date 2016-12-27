# -*- coding: utf-8 -*-

import re
import time
import random
import logging
import inspect
import itertools

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


@ircplugin.action('random')
def random_(ircbot, conf, conn, event, data):
    action = random.choice(util.split(conf['invoke']))
    if ircbot.do_action(':'.join(('action', action)), conn, event, data):
        return {}
    return None


@ircplugin.action('register')
def register(ircbot, conf, conn, event, data):
    return {conf['register'] % data: conf['value'] % data}


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


def _generate(ircbot, conf, conn, event, data):
    action = inspect.currentframe().f_back.f_code.co_name

    method = conf.get('method', 'line')
    if method not in ['line', 'raw']:
        logging.error('[%s] unknown method: %s', action, method)
        return None

    if conf.get('entrypoint', 'false').lower() == 'true':
        entrypoint = data.get('entrypoint')
    else:
        entrypoint = None

    client = util.http.APIClientV01(conf['server'], conf['port'])
    score, text = client.generate(conf['instance'], entrypoint,
                                  int(conf.get('nr_retry', 0)))
    if None in (score, text):
        logging.warn('[%s] failed to generate text', action)
        return None

    return {
        'raw':       text,
        'line':      [line for line in text.splitlines() if line],
        'method':    method,
        'registers': util.split(conf.get('registers', 'text')),
    }


@ircplugin.action('generate')
def generate(ircbot, conf, conn, event, data):
    generated = _generate(ircbot, conf, conn, event, data)
    if not generated:
        return None

    result = {}

    if generated['method'] == 'line':
        for i, reg in enumerate(generated['registers']):
            try:
                result[reg] = generated['line'][i]
            except IndexError:
                result[reg] = ''

    elif generated['method'] == 'raw':
        result[generated['registers'][0]] = generated['raw']

    return result


@ircplugin.action('talk')
def talk(ircbot, conf, conn, event, data):
    generated = _generate(ircbot, conf, conn, event, data)
    if not generated:
        return None

    for line in generated['line']:
        conn.notice(data['target'], line)
        logging.info('[talk] [%s] %s> %s',
                     data['target'], conn.get_nickname(), line)

    return {}


@ircplugin.action('suggest')
def suggest(ircbot, conf, conn, event, data):
    method = conf.get('method', 'line')
    if method not in ['line', 'word']:
        logging.error('[suggest] unknown method: %s', method)
        return None

    mapping = conf.get('mapping', 'random')
    if mapping not in ['random', 'sequential']:
        logging.error('[suggest] unknown mapping: %s', mapping)
        return None

    nr_retry = int(conf.get('nr_retry', 0))
    client = util.http.APIClientV01(conf['server'], conf['port'])
    keys = client.recent_entries(conf['instance'], nr_retry)
    if not keys:
        logging.warn('[suggest] failed to get recent entries')
        return None

    key = random.choice(keys)
    gclient = util.http.GoogleClient()
    suggested = gclient.complete(key, conf.get('locale', 'en'), nr_retry)
    if not suggested:
        logging.warn('[suggest] failed to complete with "%s"', key)
        return None

    if method == 'word':
        suggested = \
            list(itertools.chain.from_iterable(s.split() for s in suggested))

    if mapping == 'random':
        random.shuffle(suggested)

    result = {}
    for i, reg in enumerate(util.split(conf.get('registers', 'suggested'))):
        try:
            result[reg] = suggested[i]
        except IndexError:
            result[reg] = ''

    return result


@ircplugin.action('html')
def html(ircbot, conf, conn, event, data):
    if 'match' not in data or not data['match'].groups():
        logging.error('[html] cannot exec without URL pattern capture')
        return None

    url = data['match'].group(1)
    timeout = float(conf.get('timeout', 2.0))
    xpath = conf['xpath']
    content = util.http.HTML(url, timeout).getcontent(xpath)

    if content:
        content.update(url=url)
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
