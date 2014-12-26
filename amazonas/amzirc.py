# -*- coding: utf-8 -*-

import re
import random
import signal
import logging
import logging.config
import argparse
import contextlib

import irc.bot
import irc.buffer
import irc.client
import irc.schedule
import irc.functools
import irc.connection

from . import util
from . import config
from . import ircplugin

try:
    irc.client.Reactor
except AttributeError:
    irc.client.Reactor = irc.client.IRC


class DecodingLineBuffer(irc.buffer.DecodingLineBuffer):
    @property
    def encoding(self):
        return config.get('irc', 'encode')

    @property
    def errors(self):
        return 'replace'


class ServerConnection(irc.client.ServerConnection):
    buffer_class = DecodingLineBuffer

    @irc.functools.save_method_args
    def connect(self, *args, **kwargs):
        def wrapper(sock):
            orig_sender = sock.send

            def sender(data, *args, **kwargs):
                data = data.decode('utf-8', 'replace')
                data = data.encode(config.get('irc', 'encode'), 'replace')
                return orig_sender(data, *args, **kwargs)

            sock.send = sender
            return sock

        return super(ServerConnection, self).connect(
            connect_factory=irc.connection.Factory(wrapper=wrapper),
            *args, **kwargs)


class Reactor(irc.client.Reactor):
    def server(self):
        c = ServerConnection(self)
        with self.mutex:
            self.connections.append(c)
        return c

    def unregister_delayed(self, delay, func, args):
        def match(cmd, _delay, _func, _args):
            return isinstance(cmd, irc.schedule.DelayedCommand) and \
                _delay == delay and _func == func and _args == args
        return self.unregister_schedule(match)

    def unregister_every(self, delay, func, args):
        def match(cmd, _delay, _func, _args):
            return isinstance(cmd, irc.schedule.PeriodicCommand) and \
                _delay == delay and _func == func and _args == args
        return self.unregister_schedule(match)

    def unregister_schedule(self, match):
        def index():
            for i, cmd in enumerate(self.delayed_commands):
                if match(cmd, cmd.delay, cmd.function.func, cmd.function.args):
                    return i
            return -1

        removed = []

        with self.mutex:
            while True:
                idx = index()
                if idx >= 0:
                    cmd = self.delayed_commands.pop(idx)
                    removed.append((cmd.delay,
                                    cmd.function.func, cmd.function.args))
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
        self.action_active = True
        self.connection.add_global_handler('all_events', self.dispatch_event)

        try:
            self.reactor
        except AttributeError:
            self.reactor = self.ircobj

    def dispatch_event(self, conn, event):
        for handler in ircplugin.getevent(event.type):
            with exceptlog(':'.join(('event', event.type)), handler) as run:
                run(self, conn, event)

    def on_welcome(self, conn, event):
        channel = config.get('irc', 'channel')
        conn.join(channel)
        logging.info('[welcome] joined <%s>', channel)
        self.register_schedule()

    def on_nicknameinuse(self, conn, event):
        conn.nick(conn.get_nickname() + '_')

    def on_privmsg(self, conn, event):
        self.handle_message(conn, event, event.source.nick,
                            event.source.nick, event.arguments[0])

    def on_pubmsg(self, conn, event, replyto=None):
        self.handle_message(conn, event, event.source.nick,
                            event.target, event.arguments[0])

    def handle_message(self, conn, event, msgfrom, replyto, msg):
        if msg.startswith(config.get('irc', 'command_prefix') or '!'):
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
        if not self.isenabled(sect, msgfrom):
            return

        msgdata = {'msgfrom': msgfrom}
        handler = ircplugin.getcommand(words[0])

        with exceptlog(sect, handler, msg) as run:
            result = run(self, conn, event, msgfrom, replyto, *words[1:])

            if result is None:
                return

            msgdata.update(result)
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
        if sched and not self.isenabled(sched):
            return False
        if not self.isenabled(sect, msgfrom, msg):
            return False

        action = config.get(sect, 'action')
        if not action:
            logging.error('[action] [%s] no action specified', sect)
            return False

        msgdata = {'msgfrom': msgfrom}
        handler = ircplugin.getaction(action)

        with exceptlog(sect, handler, msg) as run:
            conf = config.as_dict(sect)
            result = run(self, conf, conn, event, msgfrom, replyto, msg)

            if result is None:
                return False

            msgdata.update(result)
            self.send_message(conn, replyto, sect, msgdata)

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

            self.reactor.execute_every(interval, self.do_action,
                                       (action, self.connection, None,
                                        None, channel, None, sect))
            logging.info('[schedule] [%s] registered', sect)

    def unregister_schedule(self):
        def match(cmd, delay, func, args):
            return func == self.do_action

        for delay, func, args in self.reactor.unregister_schedule(match):
            logging.info('[schedule] [%s] unregistered', args[6])

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
    def send_message(conn, replyto, sect, msgdata={}):
        message = config.get(sect, 'message')
        if message:
            f = message.encode('raw_unicode_escape').decode('unicode_escape')
            for line in (f % msgdata).splitlines():
                conn.notice(replyto, line)

    @staticmethod
    def isenabled(sect, nick=None, message=None):
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

            if nick is not None:
                if not re.search(config.get(sect, 'nick_pattern'), nick):
                    return False

            if message is not None:
                if not re.search(config.get(sect, 'pattern'), message):
                    return False
        except:
            logging.exception('[%s] nick="%s" message="%s"',
                              sect, nick, message)
            return False

        return True


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


def main():
    def setlogger(conf_file=None):
        if conf_file:
            return logging.config.fileConfig(conf_file)

        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%Y/%m/%d %H:%M:%S')

    def loadmodules(path=None):
        from . import irchandler    # load default modules

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
