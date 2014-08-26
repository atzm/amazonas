# -*- coding: utf-8 -*-

import re
import sys
import shlex
import logging
import contextlib

import irc.bot
import irc.buffer
import irc.client

import util
import config
import ircplugin
import irchandler


class IRCBot(irc.bot.SingleServerIRCBot):
    def __init__(self):
        spec = irc.bot.ServerSpec(config.get('irc', 'server'))
        port = config.getint('irc', 'port')
        password = config.get('irc', 'password')
        nick = config.get('irc', 'nick')

        if port:
            spec.port = port
        if password:
            spec.password = password

        super(IRCBot, self).__init__([spec], nick, nick)

        for name, handlers in ircplugin.iterevents():
            for handler in handlers:
                self.connection.add_global_handler(name, handler)

    def on_welcome(self, conn, event):
        channel = config.get('irc', 'channel')
        conn.join(channel)
        logging.info('joined "%s"', channel)

        for sect in sorted(config.sections()):
            if not sect.startswith('periodic_action:'):
                continue

            if not config.has_option(sect, 'action'):
                logging.warn('no action specified: %s', sect)
                continue

            action = 'action:%s' % config.get(sect, 'action')
            if not config.has_section(action):
                logging.warn('invalid action specified: %s', sect)
                continue

            interval = config.getint(sect, 'interval')
            if interval < 60:
                logging.warn('interval too short: %s', sect)
                continue

            self.connection.execute_every(interval, self._do_act,
                                          (action, self.connection, None,
                                           None, channel, None, sect))
            logging.info('registered periodic action: "%s"', sect)

    def on_nicknameinuse(self, conn, event):
        conn.nick(conn.get_nickname() + '_')

    def on_privmsg(self, conn, event):
        return self.on_pubmsg(conn, event, replyto=event.source.nick)

    def on_pubmsg(self, conn, event, replyto=None):
        msg = event.arguments[0]
        msgfrom = event.source.nick
        if replyto is None:
            replyto = event.target

        if msg.startswith('!'):
            return self._handle_command(conn, event, msgfrom, replyto, msg[1:])

        self._handle_action(conn, event, msgfrom, replyto, msg)

    def _handle_command(self, conn, event, msgfrom, replyto, msg):
        encode = config.get('irc', 'encode')

        try:
            words = [unicode(word, encode)
                     for word in shlex.split(msg.encode(encode))]
        except:
            logging.exception('parse error: "%s"', msg)
            return

        if not config.getboolean('command:%s' % words[0], 'enable'):
            return

        for handler in ircplugin.getcommand(words[0]):
            try:
                handler(self, conn, event, msgfrom, replyto, *words[1:])
            except:
                logging.exception('command error: "%s.%s" / "%s"',
                                  handler.__module__, handler.__name__, msg)

    def _handle_action(self, conn, event, msgfrom, replyto, msg):
        for sect in sorted(config.sections()):
            if not sect.startswith('action:'):
                continue
            if not config.getboolean(sect, 'enable'):
                continue

            done = self._do_act(sect, conn, event, msgfrom, replyto, msg)

            if done and not config.getboolean(sect, 'fallthrough'):
                break

    def _do_act(self, sect, conn, event, msgfrom, replyto, msg, period=None):
        if period:
            if not config.getboolean(period, 'enable'):
                return False

        if not config.has_section(sect):
            logging.warn('invalid section: %s', sect)
            return False

        try:
            time_ = config.get(sect, 'time')
            if time_ and not util.time_in(*time_.split('-', 2)):
                return False
        except:
            logging.exception('[%s] time parse failed', sect)
            return False

        action = config.get(sect, 'action')
        if not action:
            logging.error('[%s] no action specified', sect)
            return False

        pattern = config.get(sect, 'pattern')
        if not pattern:
            logging.error('[%s] no pattern specified', sect)
            return False

        try:
            regex = re.compile(pattern)
        except:
            logging.exception('[%s] pattern compilation failed', sect)
            return False

        if msg:
            match = regex.search(msg)
            if match is None:
                return False
        else:
            match = None

        for handler in ircplugin.getaction(action):
            try:
                handler(self, match, config.as_dict(sect),
                        conn, event, msgfrom, replyto, msg)
            except:
                logging.exception('[%s] action error: "%s.%s" / "%s"',
                                  sect, handler.__module__,
                                  handler.__name__, msg)

        message = config.get(sect, 'message')
        if message:
            conn.notice(replyto, message)

        return True


# XXX: python-irc is hardcoded the encoding utf-8 ...
@contextlib.contextmanager
def encoding(encode):
    orig_encode = irc.buffer.DecodingLineBuffer.encoding
    orig_send_raw = irc.client.ServerConnection.send_raw

    def send_raw(self, string, *args):
        orig_sender = self.socket.send

        def sender(data, *a):
            return orig_sender(unicode(data, 'utf-8').encode(encode), *a)

        try:
            self.socket.send = sender
            return orig_send_raw(self, string, *args)
        finally:
            self.socket.send = orig_sender

    try:
        irc.buffer.DecodingLineBuffer.encoding = encode
        irc.client.ServerConnection.send_raw = send_raw
        yield
    finally:
        irc.buffer.DecodingLineBuffer.encoding = orig_encode
        irc.client.ServerConnection.send_raw = orig_send_raw


def main():
    logging.basicConfig(level=logging.INFO)
    config.read(sys.argv[1])

    plugin_path = config.get('plugin', 'path')
    if plugin_path:
        ircplugin.load(plugin_path)

    logging.info('loaded actions:')
    for name, actions in ircplugin.iteractions():
        logging.info('  %s:', name)
        for act in actions:
            logging.info('    - %s.%s', act.__module__, act.__name__)

    logging.info('loaded commands:')
    for name, commands in ircplugin.itercommands():
        logging.info('  %s:', name)
        for comm in commands:
            logging.info('    - %s.%s', comm.__module__, comm.__name__)

    logging.info('loaded events:')
    for name, events in ircplugin.iterevents():
        logging.info('  %s:', name)
        for evt in events:
            logging.info('    - %s.%s', evt.__module__, evt.__name__)

    with encoding(config.get('irc', 'encode')):
        bot = IRCBot()
        bot.start()


if __name__ == '__main__':
    main()
