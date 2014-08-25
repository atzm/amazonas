# -*- coding: utf-8 -*-

import sys
import flask

import util
import config
import textgen


def main():
    import webapp.v01
    import webapp.instance

    if len(sys.argv) < 2:
        raise SystemExit('syntax: %s <conffile>' % sys.argv[0])

    config.read(sys.argv[1])
    util.loadmodules()
    app = flask.Flask(__name__)
    app.config['JSON_AS_ASCII'] = False

    for i in config.getlist('web', 'instances'):
        webapp.instance.register(i, textgen.TextGenerator.getinstance(i))

    try:
        app.register_blueprint(webapp.v01.mod)
        app.run(host=config.get('web', 'host'),
                port=config.getint('web', 'port'),
                debug=config.getboolean('web', 'debug'),
                use_reloader=False)
    finally:
        webapp.instance.unregister()


if __name__ == '__main__':
    main()
