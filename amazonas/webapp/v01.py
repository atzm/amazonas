# -*- coding: utf-8 -*-

import json
import flask

import amazonas.webapp.instance


mod = flask.Blueprint('v0.1', __name__, url_prefix='/v0.1')


def getinstance(instance):
    if not amazonas.webapp.instance.has(instance):
        flask.abort(404)
    return amazonas.webapp.instance.get(instance)


@mod.route('/<instance>', methods=['GET', 'PUT'])
def root(instance):
    instance = getinstance(instance)

    if flask.request.method == 'GET':
        text, sc = instance.run()
        return flask.jsonify(text=text, score=sc)

    data = flask.request.get_json()
    if 'text' not in data:
        flask.abort(400)

    if type(data['text']) is not list:
        flask.abort(400)

    for line in data['text']:
        instance.learn(line)

    return flask.Response(status=204)


@mod.route('/<instance>/keys')
def keys(instance):
    instance = getinstance(instance)
    return flask.jsonify(keys=instance.markov.db.keys())


@mod.route('/<instance>/keys/<path:keys>', methods=['GET', 'DELETE'])
def maps(instance, keys):
    instance = getinstance(instance)

    if flask.request.method == 'DELETE':
        flask.abort(501)  # not implemented

    try:
        keys = json.loads(keys)
    except:
        flask.abort(400)
    if type(keys) is not list:
        flask.abort(400)

    vals = instance.markov.db.get(tuple(keys))
    if not vals:
        flask.abort(404)

    return flask.jsonify(values=vals)


@mod.route('/<instance>/entrypoints')
def entrypoints(instance):
    instance = getinstance(instance)
    return flask.jsonify(entrypoints=instance.markov.edb.keys())


@mod.route('/<instance>/recents')
def recents(instance):
    instance = getinstance(instance)
    return flask.jsonify(recents=list(instance.recent))


@mod.route('/<instance>/stats')
def stats(instance):
    instance = getinstance(instance)
    return flask.jsonify(threshold=instance.s_thresh,
                         keys=len(instance.markov.db.keys()),
                         entrypoints=len(instance.markov.edb.keys()))
