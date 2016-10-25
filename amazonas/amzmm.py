# -*- coding: utf-8 -*-

import re
import ssl
import time
import json
import random
import urllib2
import logging
import logging.config
import argparse
import threading

import flask

from . import util
from . import config
from . import mmplugin


bp = flask.Blueprint('root', __name__)


@bp.route('/', methods=['POST'])
def root():
    if flask.request.form.get('token') != config.get('outgoing', 'token'):
        return ('', 400)

    text = OutgoingHandler(flask.request.form.to_dict()).handle()
    if text:
        return flask.jsonify(**makebody(text))

    return ('', 204)


def post(text):
    url = config.get('incoming', 'url')
    if not url:
        logging.error('[post] no incoming url specified')
        return

    ctx = ssl.create_default_context()
    if not config.getboolean('incoming', 'ssl_verify'):
        ctx = ssl._create_unverified_context()

    try:
        req = urllib2.Request(url, 'payload=' + json.dumps(makebody(text)))
        urllib2.urlopen(req, context=ctx).read()
    except:
        logging.exception('[post] %s', locals())


def makebody(text):
    try:
        icon_url = random.choice(config.getlist('mm', 'icon_url'))
    except IndexError:
        icon_url = u''

    return {
        'text':     text,
        'username': config.get('mm', 'username'),
        'icon_url': icon_url,
    }


class OutgoingHandler(object):
    def __init__(self, data=None):
        self.data = data if data is not None else {}

    @util.join(sep='\n')
    def handle(self):
        for action in config.getlist('mm', 'actions'):
            sect = ':'.join(('action', action))
            if not self.enabled(sect):
                continue

            text = self.action(sect)
            if text is not None:
                yield text

            if not config.getboolean(sect, 'fallthrough'):
                break

    def action(self, sect):
        action = config.get(sect, 'action')
        if not action:
            logging.error('[action] [%s] no action specified', sect)
            return

        try:
            func = mmplugin.getaction(action)
            conf = config.as_dict(sect)
            conf.setdefault('section', sect)

            text = func(self, conf)

            if text:
                return text

            return self.format(sect)

        except:
            logging.exception('[%s] <%s.%s> %s', sect,
                              func.__module__, func.__name__, self.data)

    def format(self, sect):
        fmt = config.get(sect, 'text')
        if not fmt:
            return

        fmt = fmt.encode('raw_unicode_escape').decode('unicode_escape')
        return fmt % self.data

    def enabled(self, sect):
        if not config.has_section(sect):
            return False

        if not config.getboolean(sect, 'enable'):
            return False

        try:
            per = config.get(sect, 'percentage')             # allow '0'
            if per and int(per) < random.randint(1, 100):
                return False

            time_ = config.get(sect, 'time')
            if time_ and not util.time_in(time_):
                return False

            if 'user_name' in self.data:
                pattern = config.get(sect, 'user_pattern')
                self.data['user_match'] = re.search(pattern,
                                                    self.data['user_name'])
                if not self.data['user_match']:
                    return False

            if 'text' in self.data:
                pattern = config.get(sect, 'pattern')
                self.data['match'] = re.search(pattern, self.data['text'])
                if not self.data['match']:
                    return False
        except:
            logging.exception('[%s] %s', sect, self.data)
            return False

        return True


class Scheduler(threading.Thread):
    def __init__(self):
        super(Scheduler, self).__init__()
        self.state = {}
        self.daemon = True

    def run(self):
        while True:
            now = time.time()
            sched = config.getlist('mm', 'schedules')

            self.clean(sched)

            for name in sched:
                self.action(now, name)

            time.sleep(1)

    def clean(self, sched):
        for name in list(self.state):
            if name not in sched:
                del self.state[name]
                logging.info('[schedule] [%s] deleted', name)

    def action(self, now, name):
        sect = ':'.join(('schedule', name))

        self.state.setdefault(name, {
            'name': name,
            'sect': sect,
            'time': now,
        })

        if not config.has_section(sect):
            logging.error('[schedule] [%s] invalid name', name)
            del self.state[name]
            return

        if not config.getboolean(sect, 'enable'):
            del self.state[name]
            return

        interval = config.getint(sect, 'interval')
        if interval < 60:
            logging.error('[schedule] [%s] interval too short', name)
            del self.state[name]
            return

        actsect = ':'.join(('action', config.get(sect, 'action')))
        if not config.has_section(actsect):
            logging.error('[schedule] [%s] invalid action', name)
            del self.state[name]
            return

        time_ = config.get(name, 'time')
        if time_ and not util.time_in(time_):
            return

        if self.state[name]['time'] + interval > now:
            return

        obj = OutgoingHandler()
        if not obj.enabled(actsect):
            return

        text = obj.action(actsect)
        if text:
            post(text)

        self.state[name]['time'] = now


def main():
    def setlogger(conf_file=None):
        if conf_file:
            return logging.config.fileConfig(conf_file)

        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%Y/%m/%d %H:%M:%S')

    def loadmodules(path=None):
        from . import mmhandler    # load default modules

        if path:
            mmplugin.load(path)

        for name, action in mmplugin.iteractions():
            logging.info('[plugin] [action] [%s] <%s.%s> loaded',
                         name, action.__module__, action.__name__)

    def getsslctx():
        crt = config.get('outgoing', 'ssl_crt')
        key = config.get('outgoing', 'ssl_key')
        return (util.abspath(crt), util.abspath(key)) if crt and key else None

    def parseargs():
        ap = argparse.ArgumentParser()
        ap.add_argument('-l', '--logging-config', type=util.abspath,
                        help='configuration file for the logging')
        ap.add_argument('config', type=util.abspath,
                        help='configuration file for the API server')
        return ap.parse_args()

    args = parseargs()

    config.read(args.config)
    setlogger(args.logging_config)
    loadmodules(config.get('plugin', 'path'))

    sslctx = getsslctx()

    app = flask.Flask(__name__)
    app.config['JSON_AS_ASCII'] = False
    app.register_blueprint(bp, url_prefix=config.get('outgoing', 'path'))

    if config.getboolean('mm', 'daemon'):
        util.daemonize()

    sched = Scheduler()
    sched.start()

    app.run(host=config.get('outgoing', 'host'),
            port=config.getint('outgoing', 'port'),
            debug=config.getboolean('mm', 'debug'),
            ssl_context=sslctx, use_reloader=False, threaded=True)


if __name__ == '__main__':
    main()
