# -*- coding: utf-8 -*-

import re
import random
import signal
import logging
import logging.config
import argparse
import functools
import contextlib

import irc.bot
import irc.client
import irc.schedule
import irc.connection

from . import util
from . import config
from . import ircplugin

try:
    irc.client.Reactor
except AttributeError:
    irc.client.Reactor = irc.client.IRC


class EncodingSocket(object):
    def __init__(self, sock):
        self.sock = sock

    def send(self, data, *args, **kwargs):
        data = data.decode('utf-8', 'replace')
        data = data.encode(config.get('irc', 'encode'), 'replace')
        return self.sock.send(data, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.sock, name)


class DecodingLineBuffer(irc.client.buffer.DecodingLineBuffer):
    @property
    def encoding(self):
        return config.get('irc', 'encode')

    @property
    def errors(self):
        return 'replace'


class ServerConnection(irc.client.ServerConnection):
    buffer_class = DecodingLineBuffer

    @property
    def connect(self):
        def wrapper(sock):
            return EncodingSocket(sock)
        connect = super(ServerConnection, self).connect
        factory = irc.connection.Factory(wrapper=wrapper)
        return functools.partial(connect, connect_factory=factory)


class Reactor(irc.client.Reactor):
    connection_class = ServerConnection

    def register_schedule(self, interval, func, *args, **kwargs):
        partial = functools.partial(func, *args, **kwargs)
        getattr(self, 'scheduler', self).execute_every(interval, partial)

    def unregister_schedule(self, match):
        if hasattr(self, 'scheduler'):
            queue = self.scheduler.queue
        else:
            queue = self.delayed_commands

        removed = []

        def func(cmd):
            if hasattr(cmd, 'target'):
                return cmd.target
            return cmd.function.func

        def index():
            for i, cmd in enumerate(queue):
                f = func(cmd)
                if not isinstance(f, functools.partial):
                    continue
                if match(f):
                    return i
            return -1

        with self.mutex:
            while True:
                idx = index()
                if idx >= 0:
                    removed.append(func(queue.pop(idx)))
                else:
                    break

        return removed


class IRCBot(irc.bot.SingleServerIRCBot):
    reactor_class = manifold_class = Reactor

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
        self.reactor = getattr(self, 'reactor', getattr(self, 'ircobj', None))
        self.action_active = True
        self.connection.add_global_handler('all_events', self.dispatch_event)

        for name, events in ircplugin.iterevents():
            if name != 'all':
                continue
            for evt in events:
                self.connection.add_global_handler(
                    'all_events', lambda c, e: evt(self, c, e), -15)

    def dispatch_event(self, conn, event):
        for handler in ircplugin.getevent(event.type):
            with exceptlog(':'.join(('event', event.type)), handler) as run:
                run(self, conn, event)

    def on_welcome(self, conn, event):
        channel = config.get('irc', 'channel')
        key = config.get('irc', 'channel_key')
        conn.join(channel, key)
        logging.info('[welcome] joined <%s>', channel)
        self.unregister_schedule()
        self.register_schedule()

    def on_nicknameinuse(self, conn, event):
        conn.nick(conn.get_nickname() + '_')

    def on_privmsg(self, conn, event):
        data = {'source': event.source.nick, 'target': event.source.nick,
                'nick0': self.connection.get_nickname(),
                'nick1': self.random_user(event.source.nick),
                'message': event.arguments[0]}
        self.handle_message(conn, event, data)

    def on_pubmsg(self, conn, event, replyto=None):
        data = {'source': event.source.nick, 'target': event.target,
                'nick0': self.connection.get_nickname(),
                'nick1': self.random_user(event.source.nick),
                'message': event.arguments[0]}
        self.handle_message(conn, event, data)

    def handle_message(self, conn, event, data):
        cprefix = config.get('irc', 'command_prefix') or '!'

        if data['message'].startswith(cprefix):
            data['message'] = data['message'][len(cprefix):]
            return self.handle_command(conn, event, data)

        self.handle_action(conn, event, data)

    def handle_command(self, conn, event, data):
        try:
            words = util.split(data['message'])
        except Exception as e:
            exc = '%s(%s)' % (e.__class__.__name__, e)
            conn.notice(data['target'], exc)
            logging.error('[command] %s: "%s"', exc, data['message'])
            return

        if not words:
            words = ['']

        sect = ':'.join(('command', words[0]))
        if not self.isenabled(sect, data):
            return

        handler = ircplugin.getcommand(words[0])

        with exceptlog(sect, handler, data) as run:
            result = run(self, conn, event, data, *words[1:])

            if result is None:
                return

            data.update(result)
            self.send_message(conn, sect, data)

    def handle_action(self, conn, event, data):
        for action in config.getlist('irc', 'actions'):
            sect = ':'.join(('action', action))
            success = self.do_action(sect, conn, event, data)
            if success and not config.getboolean(sect, 'fallthrough'):
                break

    def do_action(self, sect, conn, event, data, sched=None):
        if not self.action_active:
            return True
        if sched:
            if not self.isenabled(sched):
                return False
            data.update({
                'nick0': self.connection.get_nickname(),
                'nick1': self.random_user(self.connection.get_nickname()),
            })
        if not self.isenabled(sect, data):
            return False

        action = config.get(sect, 'action')
        if not action:
            logging.error('[action] [%s] no action specified', sect)
            return False

        handler = ircplugin.getaction(action)

        with exceptlog(sect, handler, data) as run:
            conf = config.as_dict(sect)
            conf.setdefault('section', sect)
            result = run(self, conf, conn, event, data)

            if result is None:
                return False

            data.update(result)
            self.send_message(conn, sect, data)

        chain = config.get(sect, 'chain')
        chain_sect = ':'.join(('action', chain))
        if chain and config.has_section(chain_sect):
            return self.do_action(chain_sect, conn, event, data, sched)

        return True

    def register_schedule(self):
        channel = config.get('irc', 'channel')

        for schedule in config.getlist('irc', 'schedules'):
            sect = ':'.join(('schedule', schedule))

            # do not evaluate isenabled() here.
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

            self.reactor.register_schedule(interval, self.do_action,
                                           action, self.connection,
                                           None, {'target': channel}, sect)
            logging.info('[schedule] [%s] registered', sect)

    def unregister_schedule(self):
        def match(func):
            return func.func == self.do_action

        for func in self.reactor.unregister_schedule(match):
            logging.info('[schedule] [%s] unregistered', func.args[4])

    def random_user(self, default):
        try:
            return random.choice(self.users)
        except IndexError:
            pass
        return default

    @property
    def users(self):
        channel = config.get('irc', 'channel')
        nick = self.connection.get_nickname()
        return list(set(self.channels[channel].users()) - set([nick]))

    @property
    def opers(self):
        channel = config.get('irc', 'channel')
        nick = self.connection.get_nickname()
        return list(set(self.channels[channel].opers()) - set([nick]))

    @property
    def noopers(self):
        return list(set(self.users) - set(self.opers))

    @property
    def isoper(self):
        channel = config.get('irc', 'channel')
        nick = self.connection.get_nickname()
        return self.channels[channel].is_oper(nick)

    @staticmethod
    def send_message(conn, sect, data):
        message = config.get(sect, 'message')
        if message:
            f = message.encode('raw_unicode_escape').decode('unicode_escape')
            for line in (f % data).splitlines():
                conn.notice(data['target'], line)
                logging.info('[%s] [%s] %s> %s', sect, data['target'],
                             conn.get_nickname(), line)

    @staticmethod
    def isenabled(sect, data={}):
        if not config.has_section(sect):
            return False

        if not config.getboolean(sect, 'enable'):
            return False

        try:
            per = config.get(sect, 'percentage')             # allow '0'
            if per and int(per) < random.randint(1, 100):
                return False

            time_ = config.get(sect, 'time')
            if time_ and not util.time_in(time_):
                return False

            if 'source' in data:
                pattern = config.get(sect, 'source_pattern')
                data['source_match'] = re.search(pattern, data['source'])
                if not data['source_match']:
                    return False

            if 'message' in data:
                pattern = config.get(sect, 'pattern')
                data['match'] = re.search(pattern, data['message'])
                if not data['match']:
                    return False
        except Exception:
            logging.exception('[%s] %s', sect, data)
            return False

        return True


@contextlib.contextmanager
def exceptlog(name, func, data={}):
    try:
        yield func
    except Exception as e:
        msg = '[%s] %s(%s): <%s.%s>' % (name, e.__class__.__name__, e,
                                        func.__module__, func.__name__)
        if data:
            msg += ' / %s' % data

        logging.exception(msg)


def main():
    def setlogger(conf_file=None):
        if conf_file:
            return logging.config.fileConfig(conf_file)

        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%Y/%m/%d %H:%M:%S')

    def loadmodules(path=None):
        # load default modules
        from . import irchandler  # noqa: F401

        if path:
            ircplugin.load(path)

        for name, action in ircplugin.iteractions():
            logging.info('[plugin] [action] [%s] <%s.%s> loaded',
                         name, action.__module__, action.__name__)
        for name, command in ircplugin.itercommands():
            logging.info('[plugin] [command] [%s] <%s.%s> loaded',
                         name, command.__module__, command.__name__)
        for name, events in ircplugin.iterevents():
            for evt in events:
                logging.info('[plugin] [event] [%s] <%s.%s> loaded',
                             name, evt.__module__, evt.__name__)

    ap = argparse.ArgumentParser()
    ap.add_argument('-l', '--logging-config', type=util.abspath,
                    help='configuration file for the logging')
    ap.add_argument('config', type=util.abspath,
                    help='configuration file for the IRC client')
    args = ap.parse_args()

    config.read(args.config)
    setlogger(args.logging_config)
    loadmodules(config.get('plugin', 'path'))

    bot = IRCBot()

    def q(*args, **kwargs):
        bot.die(config.get('irc', 'quit_message'))
        raise SystemExit()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, q)

    if config.getboolean('irc', 'daemon'):
        util.daemonize()

    with exceptlog('main', bot.start) as run:
        run()


if __name__ == '__main__':
    main()
