import logging

import aiotask_context as context


class AppLogging:
    def __init__(self):
        self.log = logging.getLogger('application')
        self.context = context

    def info(self, msg):
        self.log.info('{0} {1}'.format(self.context.get('X-Request-ID'), msg))

    def warning(self, msg):
        self.log.warning('{0} {1}'.format(self.context.get('X-Request-ID'), msg))

    def error(self, msg):
        self.log.error('{0} {1}'.format(self.context.get('X-Request-ID'), msg))

    def critical(self, msg):
        self.log.critical('{0} {1}'.format(self.context.get('X-Request-ID'), msg))

    def fatal(self, msg):
        self.log.fatal('{0} {1}'.format(self.context.get('X-Request-ID'), msg))

    def debug(self, msg):
        self.log.debug('{0} {1}'.format(self.context.get('X-Request-ID'), msg))
