# -*- coding: utf-8 -*-

import re
import os
import sys
import signal
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
        self.register_events()

    def on_welcome(self, conn, event):
        channel = config.get('irc', 'channel')
        conn.join(channel)
        logging.info('[welcome] joined <%s>', channel)
        self.schedule()

    def on_nicknameinuse(self, conn, event):
        conn.nick(conn.get_nickname() + '_')

    def on_privmsg(self, conn, event):
        self.handle_message(conn, event, event.source.nick,
                            event.source.nick, event.arguments[0])

    def on_pubmsg(self, conn, event, replyto=None):
        self.handle_message(conn, event, event.source.nick,
                            event.target, event.arguments[0])

    def send_message(self, conn, replyto, sect, msgdata={}):
        message = config.get(sect, 'message')
        if message:
            with exceptlog(sect, conn.notice, message) as run:
                run(replyto, message % msgdata)

    def handle_message(self, conn, event, msgfrom, replyto, msg):
        if msg.startswith('!'):
            return self.handle_command(conn, event, msgfrom, replyto, msg[1:])

        self.handle_action(conn, event, msgfrom, replyto, msg)

    def handle_command(self, conn, event, msgfrom, replyto, msg):
        try:
            words = util.split(msg)
        except Exception as e:
            conn.notice(replyto, str(e))
            logging.error('[command] %s: "%s"', str(e), msg)
            return

        sect = ':'.join(('command', words[0]))
        if not config.enabled(sect):
            return

        msgdata = {'msgfrom': msgfrom}
        for handler in ircplugin.getcommand(words[0]):
            with exceptlog(sect, handler, msg) as run:
                r = run(self, conn, event, msgfrom, replyto, *words[1:])
                if type(r) is dict:
                    msgdata.update(r)

        self.send_message(conn, replyto, sect, msgdata)

    def handle_action(self, conn, event, msgfrom, replyto, msg):
        for action in config.getlist('irc', 'actions'):
            sect = ':'.join(('action', action))
            success = self.do_action(sect, conn, event, msgfrom, replyto, msg)
            if success and not config.getboolean(sect, 'fallthrough'):
                break

    def do_action(self, sect, conn, event, msgfrom, replyto, msg, sched=None):
        if not self.action_active:
            return True
        if sched and not config.enabled(sched):
            return False
        if not config.enabled(sect):
            return False

        action = config.get(sect, 'action')
        if not action:
            logging.error('[action] [%s] no action specified', sect)
            return False

        if msg:
            try:
                match = self.do_match(sect, msg)
            except Exception as e:
                logging.error('[action] [%s] %s', sect, str(e))
                return False
            if not match:
                return False
        else:
            match = None

        msgdata = {'msgfrom': msgfrom}
        for handler in ircplugin.getaction(action):
            with exceptlog(sect, handler, msg) as run:
                conf = config.as_dict(sect)
                r = run(self, match, conf, conn, event, msgfrom, replyto, msg)
                if type(r) is dict:
                    msgdata.update(r)

        self.send_message(conn, replyto, sect, msgdata)
        return True

    def do_match(self, sect, msg):
        pattern = config.get(sect, 'pattern')
        if not pattern:
            raise ValueError('no pattern specified')

        return re.search(pattern, msg)

    def schedule(self):
        channel = config.get('irc', 'channel')

        for schedule in config.getlist('irc', 'schedules'):
            sect = ':'.join(('schedule', schedule))

            # do not evaluate config.enabled() here.
            # if it does, the disabled action will never be scheduled.
            if not config.has_section(sect):
                logging.error('[schedule] [%s] no such schedule', sect)
                continue

            if not config.has_option(sect, 'action'):
                logging.error('[schedule] [%s] no action specified', sect)
                continue

            action = ':'.join(('action', config.get(sect, 'action')))
            if not config.has_section(action):
                logging.error('[schedule] [%s] invalid action specified', sect)
                continue

            interval = config.getint(sect, 'interval')
            if interval < 60:
                logging.error('[schedule] [%s] interval too short', sect)
                continue

            self.connection.execute_every(interval, self.do_action,
                                          (action, self.connection, None,
                                           None, channel, None, sect))
            logging.info('[schedule] [%s] registered', sect)

    def register_events(self):
        for name, handlers in ircplugin.iterevents():
            for handler in handlers:
                self.connection.add_global_handler(name, handler)


@contextlib.contextmanager
def exceptlog(name, func, message=None):
    try:
        yield func
    except Exception as e:
        msg = '[%s] %s: <%s.%s>' % (name, str(e),
                                    func.__module__, func.__name__)
        if message:
            msg += ' / "%s"' % message

        logging.exception(msg)


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
        for name, actions in ircplugin.iteractions():
            for act in actions:
                logging.info('[plugin] [action] [%s] <%s.%s> loaded',
                             name, act.__module__, act.__name__)

        for name, commands in ircplugin.itercommands():
            for comm in commands:
                logging.info('[plugin] [command] [%s] <%s.%s> loaded',
                             name, comm.__module__, comm.__name__)

        for name, events in ircplugin.iterevents():
            for evt in events:
                logging.info('[plugin] [event] [%s] <%s.%s> loaded',
                             name, evt.__module__, evt.__name__)

    logging_config = None

    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], 'l:')
    except getopt.error:
        usage()

    for opt, optarg in opts:
        if opt == '-l':
            logging_config = util.abspath(optarg)

    if not args:
        usage()

    config.read(util.abspath(args[0]))

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

        def q(*args, **kwargs):
            bot.die(config.get('irc', 'quit_message'))
            raise SystemExit()

        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, q)

        with exceptlog('main', bot.start) as run:
            run()


if __name__ == '__main__':
    main()
