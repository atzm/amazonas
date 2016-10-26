# -*- coding: utf-8 -*-

import re
import random
import logging

from .. import util
from .. import config
from .. import mmplugin


@mmplugin.action('null')
def null(obj, conf):
    pass


@mmplugin.action('log')
def log_(obj, conf):
    level = conf.get('level', 'info')
    fmt = conf.get('format', '')
    fmt = fmt.encode('raw_unicode_escape').decode('unicode_escape')
    body = (fmt % obj.data).replace('\n', r'\n')
    getattr(logging, level, logging.info)(body)


@mmplugin.action('reload')
def reload(obj, conf):
    config.reload()
    logging.info('[reload] config reloaded')


@mmplugin.action('random')
def random_(obj, conf):
    action = random.choice(util.split(conf['invoke']))
    return obj.action(':'.join(('action', action)))


@mmplugin.action('replace')
def replace(obj, conf):
    if 'text' not in obj.data:
        logging.error('[replace] cannot exec without text')
        return

    regex = conf['regex']
    replace = conf['replace'] % obj.data

    # replace action manipulates the text itself,
    # so it affects pattern matching of next actions.
    obj.data.update(text=re.sub(regex, replace, obj.data['text']))


@mmplugin.action('learn')
def learn(obj, conf):
    if 'text' not in obj.data:
        logging.error('[learn] cannot exec without text')
        return

    # learn action manipulates the text temporarily,
    # so it does not affect any other actions.
    text = obj.data['text']
    replace_regex = conf.get('replace_regex')
    replace_with = conf.get('replace_with')
    if replace_regex and replace_with is not None:
        replace_with = replace_with % obj.data
        text = re.sub(replace_regex, replace_with, text)

    retry = int(conf.get('nr_retry', 0))
    client = util.http.APIClientV01(conf['server'], conf['port'])
    if not client.learn(conf['instance'], [text], retry):
        logging.warn('[learn] failed to learn "%s"', text.replace('\n', r'\n'))


@mmplugin.action('talk')
def talk(obj, conf):
    client = util.http.APIClientV01(conf['server'], conf['port'])
    score, text = client.generate(conf['instance'],
                                  int(conf.get('nr_retry', 0)))
    if None in (score, text):
        logging.warn('[talk] failed to generate text')
        return

    logging.info('[talk] %s', text.replace('\n', r'\n'))
    return text


@mmplugin.action('suggest')
def suggest(obj, conf):
    nr_retry = int(conf.get('nr_retry', 0))
    client = util.http.APIClientV01(conf['server'], conf['port'])
    keys = client.recent_entries(conf['instance'], nr_retry)
    if not keys:
        logging.warn('[suggest] failed to get recent entries')
        return

    key = random.choice(keys)
    gclient = util.http.GoogleClient()
    result = gclient.complete(key, conf.get('locale', 'en'), nr_retry)
    if not result:
        logging.warn('[suggest] failed to complete with "%s"', key)
        return

    obj.data.update(suggested=random.choice(result))


@mmplugin.action('html')
def html(obj, conf):
    if 'match' not in obj.data or not obj.data['match'].groups():
        logging.error('[html] cannot exec without URL pattern capture')
        return

    url = obj.data['match'].group(1)
    timeout = float(conf.get('timeout', 2.0))
    xpath = conf['xpath']
    content = util.http.HTML(url, timeout).getcontent(xpath)

    if content:
        obj.data.update(url=url, **content)
        return

    logging.warn('[html] failed to get %s on %s', xpath, url)
