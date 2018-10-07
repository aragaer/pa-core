import logging
import select
import time

from runner.channel import SocketChannel


_LOGGER = logging.getLogger(__name__)


class Poller:

    def __init__(self):
        self._servers = {}
        self._channels = {}
        self._poll = select.poll()

    def poll(self, timeout=None):
        if timeout is not None:
            timeout = timeout * 1000
        result = []
        for fd, event in self._poll.poll(timeout):
            if fd in self._channels:
                channel = self._channels[fd]
                data = channel.read()
                result.append((data, channel))
            else:
                server = self._servers[fd]
                sock, _ = server.accept()
                self.register(SocketChannel(sock))
        return result

    def register(self, channel):
        fd = channel.get_fd()
        self._channels[fd] = channel
        self._poll.register(fd, select.POLLIN)
        _LOGGER.debug("Registered channel %s with fd %d", channel, fd)

    def add_server(self, server):
        self._servers[server.fileno()] = server
        self._poll.register(server.fileno())

    def close_all(self):
        for channel in self._channels.values():
            channel.close()
        for server in self._servers.values():
            server.close()
