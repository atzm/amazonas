# -*- coding: utf-8 -*-

import sys
import flask

from . import util
from . import config
from . import textgen


def main():
    from .webapp import v01
    from .webapp import instance

    if len(sys.argv) < 2:
        raise SystemExit('syntax: %s <conffile>' % sys.argv[0])

    config.read(sys.argv[1])
    util.loadmodules()
    app = flask.Flask(__name__)
    app.config['JSON_AS_ASCII'] = False

    for i in config.getlist('web', 'instances'):
        instance.register(i, textgen.TextGenerator.getinstance(i))

    try:
        app.register_blueprint(v01.mod)
        app.run(host=config.get('web', 'host'),
                port=config.getint('web', 'port'),
                debug=config.getboolean('web', 'debug'),
                use_reloader=False)
    finally:
        instance.unregister()


if __name__ == '__main__':
    main()
