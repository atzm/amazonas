# -*- coding: utf-8 -*-

instances = {}


def register(name, obj):
    instances[name] = obj


def unregister():
    instances.clear()


def has(name):
    return name in instances


def get(name):
    return instances[name]
