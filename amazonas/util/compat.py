# -*- coding: utf-8 -*-

import six


def isnum(data):
    return isinstance(data, six.integer_types + (float,))


def isucode(data):
    return isinstance(data, six.text_type)


def ucode(data, *args, **kwargs):
    if isinstance(data, six.binary_type):
        return data.decode(*args, **kwargs)
    return data
