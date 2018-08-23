import os
import shutil
import unittest

from tempfile import mkdtemp

from core import Config, Kapellmeister
from utils import timeout


class KapellmeisterTest(unittest.TestCase):

    def test_no_components(self):
        km = Kapellmeister(Config("components:\n"))

        km.run()

    def test_one_component(self):
        cfg = '''
            components:
              echo:
                command: echo hello, world
        '''
        km = Kapellmeister(Config(cfg))
        km.run()

        channel = km.connect("echo")

        with timeout(1):
            line = b''
            while not line.endswith(b'\n'):
                line += channel.read()
        self.assertEqual(line, b'hello, world\n')

    def test_two_components(self):
        dirname = mkdtemp()
        sock = os.path.join(dirname, "sock")
        self.addCleanup(shutil.rmtree, dirname)
        cfg = '''
            components:
              socat1:
                command: socat STDIO UNIX-LISTEN:{sock}
              socat2:
                command: socat UNIX:{sock} STDIO
                after: socat1
        '''.format(sock=sock)
        km = Kapellmeister(Config(cfg))
        km.run()

        channel1 = km.connect("socat1")
        channel2 = km.connect("socat2")

        channel1.write(b'howdy\n')

        with timeout(1):
            line = b''
            while not line.endswith(b'\n'):
                line += channel2.read()
        self.assertEqual(line, b'howdy\n')
