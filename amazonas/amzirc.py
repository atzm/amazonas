# -*- coding: utf-8 -*-

import re
import os
import sys
import getopt
import logging
import logging.config
import contextlib

import irc.bot
import irc.buffer
import irc.client

from . import util
from . import config
from . import ircplugin
from . import irchandler


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
        self.action_active = True

        for name, handlers in ircplugin.iterevents():
            for handler in handlers:
                self.connection.add_global_handler(name, handler)

    def on_welcome(self, conn, event):
        channel = config.get('irc', 'channel')
        conn.join(channel)
        logging.info('joined channel "%s"', channel)
        self._register_periodic(channel)

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
            words = util.split(msg, encode)
        except:
            logging.exception('parse error: "%s"', msg)
            return

        sect = 'command:%s' % words[0]

        if not config.enabled(sect):
            return

        for handler in ircplugin.getcommand(words[0]):
            try:
                handler(self, conn, event, msgfrom, replyto, *words[1:])
            except:
                logging.exception('command error: "%s.%s" / "%s"',
                                  handler.__module__, handler.__name__, msg)

        self._send_message(conn, replyto, sect)

    def _handle_action(self, conn, event, msgfrom, replyto, msg):
        for sect in sorted(config.sections()):
            if not sect.startswith('action:'):
                continue

            succeeded = self._do_act(sect, conn, event, msgfrom, replyto, msg)
            if succeeded and not config.getboolean(sect, 'fallthrough'):
                break

    def _do_act(self, sect, conn, event, msgfrom, replyto, msg, period=None):
        if not self.action_active:
            return True

        if period:
            if not config.enabled(period):
                return False

        if not config.enabled(sect):
            return False

        action = config.get(sect, 'action')
        if not action:
            logging.error('[%s] no action specified', sect)
            return False

        if msg:  # if not periodic run
            pattern = config.get(sect, 'pattern')
            if not pattern:
                logging.error('[%s] no pattern specified', sect)
                return False

            try:
                regex = re.compile(pattern)
            except:
                logging.exception('[%s] pattern compilation failed', sect)
                return False

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

        self._send_message(conn, replyto, sect)
        return True

    def _register_periodic(self, channel):
        for sect in sorted(config.sections()):
            if not sect.startswith('periodic_action:'):
                continue

            # do not evaluate config.enabled() while registering.
            # if do, the disabled action will not be registered forever.

            if not config.has_option(sect, 'action'):
                logging.error('no action specified: %s', sect)
                continue

            action = 'action:%s' % config.get(sect, 'action')
            if not config.has_section(action):
                logging.error('invalid action specified: %s', sect)
                continue

            interval = config.getint(sect, 'interval')
            if interval < 60:
                logging.error('interval too short, ignored: %s', sect)
                continue

            self.connection.execute_every(interval, self._do_act,
                                          (action, self.connection, None,
                                           None, channel, None, sect))
            logging.info('registered periodic action: "%s"', sect)

    def _send_message(self, conn, replyto, sect):
        message = config.get(sect, 'message')
        if message:
            conn.notice(replyto, message)


# XXX: python-irc is hardcoded the encoding utf-8 ...
@contextlib.contextmanager
def encoding(encode):
    orig_encode = irc.buffer.DecodingLineBuffer.encoding
    orig_errors = irc.buffer.DecodingLineBuffer.errors
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
        irc.buffer.DecodingLineBuffer.errors = 'replace'
        irc.client.ServerConnection.send_raw = send_raw
        yield
    finally:
        irc.buffer.DecodingLineBuffer.encoding = orig_encode
        irc.buffer.DecodingLineBuffer.errors = orig_errors
        irc.client.ServerConnection.send_raw = orig_send_raw


def main():
    def usage():
        raise SystemExit('syntax: %s [-l <logging_config>] <config>' %
                         os.path.basename(sys.argv[0]))

    def log_modules():
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

    plugin_path = config.get('plugin', 'path')
    if plugin_path:
        ircplugin.load(plugin_path)

    if logging_config:
        logging.config.fileConfig(logging_config)
    else:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%Y/%m/%d %H:%M:%S')

    log_modules()

    if config.getboolean('irc', 'daemon'):
        util.daemonize()

    with encoding(config.get('irc', 'encode')):
        bot = IRCBot()
        bot.start()


if __name__ == '__main__':
    main()