# -*- coding: utf-8 -*-

import signal
import logging
import logging.config
import argparse

import flask

from . import db
from . import util
from . import parser
from . import config
from . import textgen

from .webapp import v01
from .webapp import instance


def main():
    def loadmodules():
        for m in config.getlist('module', 'parsers'):
            parser.loadmodule(m)
        for m in config.getlist('module', 'databases'):
            db.loadmodule(m)

    def runapp(name):
        app = flask.Flask(name)
        app.config['JSON_AS_ASCII'] = False
        app.register_blueprint(v01.mod)
        app.run(host=config.get('web', 'host'),
                port=config.getint('web', 'port'),
                debug=config.getboolean('web', 'debug'),
                use_reloader=False)

    def q(*args, **kwargs):
        raise SystemExit()

    ap = argparse.ArgumentParser()
    ap.add_argument('-l', '--logging-config', type=util.abspath,
                    help='configuration file for the logging')
    ap.add_argument('config', type=util.abspath,
                    help='configuration file for the API server')
    args = ap.parse_args()

    config.read(args.config)
    loadmodules()

    if args.logging_config:
        logging.config.fileConfig(args.logging_config)

    if config.getboolean('web', 'daemon'):
        util.daemonize()

    for i in config.getlist('web', 'instances'):
        instance.register(i, textgen.TextGenerator.getinstance(i))

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, q)

    try:
        runapp(__name__)
    finally:
        instance.unregister()


if __name__ == '__main__':
    main()
