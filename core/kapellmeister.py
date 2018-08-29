import atexit
import logging
import re
import os
import shlex
import shutil

from tempfile import mkdtemp

from runner import Runner

_LOGGER = logging.getLogger(__name__)

_VAR_RE = re.compile(r'\${(\w+)}')


class Kapellmeister:

    def __init__(self, config):
        self._config = config
        self._runner = Runner()
        self._dir = None

    def _repl_var(self, matchobj):
        return self._config.variables[matchobj.group(1)]['value']

    def run(self):
        self._dir = mkdtemp()
        atexit.register(shutil.rmtree, self._dir)
        for var, val in self._config.variables.items():
            val['value'] = os.path.join(self._dir, var)

        for component, definition in self._config.components.items():
            command = _VAR_RE.sub(self._repl_var, definition['command'])
            _LOGGER.debug("'%s' -> '%s'", definition['command'], command)
            definition['command'] = command

        self._runner.update_config(self._config.components)
        for component in self._config.components:
            self._runner.ensure_running(component)

    def connect(self, component):
        return self._runner.get_channel(component)

    def get_variable(self, variable_name):
        return self._config.variables[variable_name]['value']
