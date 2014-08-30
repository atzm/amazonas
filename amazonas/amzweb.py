# -*- coding: utf-8 -*-

import os
import sys
import getopt
import logging
import logging.config

import flask

from . import db
from . import util
from . import parser
from . import config
from . import textgen

from .webapp import v01
from .webapp import instance


def main():
    def usage():
        raise SystemExit('syntax: %s [-l <logging_config>] <config>' %
                         os.path.basename(sys.argv[0]))

    def load_modules():
        for m in config.getlist('module', 'parsers'):
            parser.loadmodule(m)

        for m in config.getlist('module', 'databases'):
            db.loadmodule(m)

    def run_app(name):
        app = flask.Flask(name)
        app.config['JSON_AS_ASCII'] = False
        app.register_blueprint(v01.mod)
        app.run(host=config.get('web', 'host'),
                port=config.getint('web', 'port'),
                debug=config.getboolean('web', 'debug'),
                use_reloader=False)

    logging_config = None

    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], 'l:')
    except getopt.error:
        usage()

    for opt, optarg in opts:
        if opt == '-l':
            logging_config = os.path.abspath(optarg)

    if not args:
        usage()

    config.read(os.path.abspath(args[0]))
    load_modules()

    if logging_config:
        logging.config.fileConfig(logging_config)

    if config.getboolean('web', 'daemon'):
        util.daemonize()

    for i in config.getlist('web', 'instances'):
        instance.register(i, textgen.TextGenerator.getinstance(i))

    try:
        run_app(__name__)
    finally:
        instance.unregister()


if __name__ == '__main__':
    main()
