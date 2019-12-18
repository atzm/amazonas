# -*- coding: utf-8 -*-

import os

from . import compat

from lxml import html
from six.moves import urllib


_BASE_URL = 'http://j-lyric.net/'


def _get_url(artist_id, title_id=None):
    url = _BASE_URL + '/'.join(('artist', artist_id, ''))

    if title_id is not None:
        url += title_id + '.html'

    return url


def _split_url(url):
    x = url.split('/')

    if url.endswith('.html'):
        return x[-2], os.path.splitext(x[-1])[0]

    return x[-2], None


def search(title=None, artist=None, lyrics=None, ct=2, ca=2, cl=2, p=1):
    q = {'ct': ct, 'ca': ca, 'cl': cl, 'p': p}

    if title:
        q.update({'kt': title.encode('utf-8')})
    if artist:
        q.update({'ka': artist.encode('utf-8')})
    if lyrics:
        q.update({'kl': lyrics.encode('utf-8')})

    try:
        url = _BASE_URL + '?'.join(('index.php', urllib.parse.urlencode(q)))
        root = html.parse(url).getroot()
        body = root.get_element_by_id('lyricList')
    except (KeyError, IOError):
        raise StopIteration()

    for b in body.find_class('body'):
        t = b.find_class('title')[0].getchildren()[0]
        title = t.text_content()
        artist_id, title_id = _split_url(t.attrib['href'])
        artist = b.find_class('status')[0].getchildren()[0].text_content()
        yield title, title_id, artist, artist_id


def get(artist_id, title_id):
    try:
        root = html.parse(_get_url(artist_id, title_id)).getroot()
        body = root.get_element_by_id('Lyric')
        return '\n'.join(' '.join(t.split()) for t in body.itertext())
    except (KeyError, IOError):
        return None


def get_artist_id(name):
    for _, _, artist, artist_id in search(artist=name, ca=1):
        if name == artist:
            return artist_id
    return None


def itertitles(artist_id):
    try:
        root = html.parse(_get_url(artist_id)).getroot()
        body = root.get_element_by_id('cnt')
    except (KeyError, IOError):
        raise StopIteration()

    for x in body.find_class('ttl'):
        x = x.getchildren()[0]
        title = x.text_content()
        _, title_id = _split_url(x.attrib['href'])
        yield title, title_id


if __name__ == '__main__':
    import sys
    import time
    import errno
    import codecs
    import random

    artist = compat.ucode(sys.argv[1], sys.getfilesystemencoding())
    artist_id = get_artist_id(artist)
    time.sleep(random.randint(1, 5))

    if not artist_id:
        raise SystemExit('artist not found')

    try:
        os.mkdir(artist_id, 0o755)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    for title, title_id in itertitles(artist_id):
        time.sleep(random.randint(3, 15))

        path = os.path.join(artist_id, title_id) + '.txt'
        lyrics = get(artist_id, title_id)

        if not lyrics:
            print('could not get %s/%s' % (artist_id, title_id))
            continue

        with codecs.open(path, 'w', encoding='utf-8') as fp:
            fp.write(lyrics)

        print('dumped %s' % path)
