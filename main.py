#!/usr/bin/env python3

import atexit
import logging
import os
import socket
import subprocess
import sys
import time

from router.routing import Faucet, Router, PipeFaucet, Sink, PipeSink, Rule, SocketFaucet, SocketSink


class OldTgFaucet(SocketFaucet):

    def __init__(self, sock, owner_id):
        super().__init__(sock)
        self._owner = owner_id
        sock.send(b'register backend\n')

    def read(self):
        """Almost exact copy of SocketFaucet.read"""
        pos = self._buf.find("\n")
        if pos == -1:
            try:
                data = self._sock.recv(4096).decode()
                if not data:
                    raise EndpointClosedException()
                self._buf += data
            except BlockingIOError:
                pass
            pos = self._buf.find("\n")
        if pos == -1:
            return
        line, self._buf = self._buf[:pos], self._buf[pos+1:]
        if line.startswith("message:"):
            line = line[8:].strip()
        return {"from": {"media": "telegram", "id": self._owner},
                "text": line}


class OldTgSink(SocketSink):

    def write(self, message):
        """Almost exact copy of SocketSink.write"""
        try:
            self._sock.send("message: {}\n".format(message['text']).encode())
        except BrokenPipeError:
            raise EndpointClosedException()


class TgFaucet(Faucet):

    def __init__(self, base_faucet):
        self._base = base_faucet

    def read(self):
        event = self._base.read()
        if event and 'message' in event:
            message = event['message']
            message['from']['media'] = 'telegram'
            return message


class TgSink(Sink):

    def __init__(self, base_sink):
        self._base = base_sink

    def write(self, message):
        if 'chat_id' not in message:
            message['chat_id'] = 43543351
            message['text'] = "Не знаю, кому отправить: {}".format(message['text'])
        super().write(message)


class DumpSink(Sink):

    def __init__(self, logname):
        self._logger = logging.getLogger(logname)

    def write(self, message):
        self._logger.debug("Dropped %s", message)


def main(owner_id, sock_name):
    logger = logging.getLogger("router")
    router = Router(DumpSink('dumped'))
    router.add_sink(DumpSink('seen'), 'from_me')

    if False:
        tg_proc = subprocess.Popen([".env/bin/python3", "single_stdio.py"],
                                cwd="tg",
                                stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE)

        faucet = TgFaucet(PipeFaucet(tg_proc.stdout.fileno()))
    else:
        tg_proc = subprocess.Popen([".env/bin/python3", "pa.py"],
                                   cwd="tg")
        sock = socket.socket(socket.AF_UNIX)
        path = "tg/"+sock_name
        logging.getLogger("main").info("connecting to %s", path)
        while not os.path.exists(path):
            time.sleep(1)
        sock.connect(path)
        faucet = OldTgFaucet(sock, owner_id)
        router.add_sink(OldTgSink(sock), "tg")
    atexit.register(tg_proc.terminate)
    router.add_faucet(faucet, "tg")
    router.add_rule(Rule('brain', id=owner_id), 'tg')

    brain_sock_path = "brain/socket"
    if os.path.exists(brain_sock_path):
        os.unlink(brain_sock_path)
    brain_proc = subprocess.Popen(["sbcl", "--script", "run.lisp", "--socket", "socket"],
                                  cwd="brain")
    atexit.register(brain_proc.terminate)

    brain_sock = socket.socket(socket.AF_UNIX)
    logging.getLogger("main").info("connecting to %s", brain_sock_path)
    while not os.path.exists(brain_sock_path):
        time.sleep(1)
    brain_sock.connect(brain_sock_path)
    router.add_sink(SocketSink(brain_sock), "brain")

    router.add_faucet(SocketFaucet(brain_sock), "brain")
    router.add_rule(Rule("tg"), "brain")
    while True:
        router.tick()
        time.sleep(1)


if __name__ == '__main__':
    sock_name = "socket"
    with open('tg/token.txt') as token_file:
        for line in token_file:
            key, value = line.split()
            if key == 'OWNER':
                owner_id = int(value)
            elif key == 'SOCKET':
                sock_name = value.strip()
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    logging.getLogger("dump").setLevel(logging.DEBUG)
    main(owner_id, sock_name)
