# -*- coding: utf-8 -*-

import json
import flask

from . import instance


mod = flask.Blueprint('v0.1', __name__, url_prefix='/v0.1')


def getinstance(inst):
    if not instance.has(inst):
        flask.abort(404)
    return instance.get(inst)


@mod.route('/<inst>', methods=['GET', 'PUT'])
def root(inst):
    inst = getinstance(inst)

    if flask.request.method == 'GET':
        text, sc = inst.run()
        if text is not None and sc is not None:
            return flask.jsonify(text=text, score=sc)
        return flask.Response(status=204)

    data = flask.request.get_json()
    if 'text' not in data:
        flask.abort(400)

    if type(data['text']) is not list:
        flask.abort(400)

    for line in data['text']:
        inst.learn(line)

    return flask.Response(status=204)


@mod.route('/<inst>/keys')
def keys(inst):
    inst = getinstance(inst)
    return flask.jsonify(keys=inst.markov.keys())


@mod.route('/<inst>/keys/<path:keys>')
def values(inst, keys):
    inst = getinstance(inst)

    try:
        keys = json.loads(keys)
    except:
        flask.abort(400)
    if type(keys) is not list:
        flask.abort(400)

    vals = inst.markov.values(keys)
    if not vals:
        flask.abort(404)

    return flask.jsonify(values=vals)


@mod.route('/<inst>/entrypoints')
def entrypoints(inst):
    inst = getinstance(inst)
    return flask.jsonify(keys=inst.markov.entrypoints())


@mod.route('/<inst>/recent-entrypoints')
def recent_entrypoints(inst):
    inst = getinstance(inst)
    return flask.jsonify(keys=list(inst.entrypoint))


@mod.route('/<inst>/histories')
def histories(inst):
    inst = getinstance(inst)
    return flask.jsonify(histories=list(inst.history))


@mod.route('/<inst>/stats')
def stats(inst):
    inst = getinstance(inst)
    return flask.jsonify(threshold=inst.score_threshold,
                         maxchain=inst.markov.maxchain,
                         keys=inst.markov.key_length(),
                         entrypoints=inst.markov.entrypoint_length())
