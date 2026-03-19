import logging
from logging.config import dictConfig


class Logger:
    def __init__(self, name=None, level="INFO", file_path=None, stream='ext://sys.stdout'):
        config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {'default': {
                'format': '%(asctime)s %(levelname)s  [%(threadName)s] %(module)s - %(message)s'
            }},
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'stream': stream,
                    'formatter': 'default'
                }
            },
            'root': {
                'level': level,
                'handlers': ['console']
            }
        }

        # Add file handler only if file_path is provided
        if file_path:
            try:
                # Test if we can write to the file
                with open(file_path, 'a'):
                    pass

                config['handlers']['fileHandler'] = {
                    'level': level,
                    'formatter': 'default',
                    'class': 'logging.FileHandler',
                    'mode': 'a',
                    'filename': file_path
                }
                config['root']['handlers'].append('fileHandler')
            except (IOError, PermissionError) as e:
                print(f"Warning: Could not configure file logging to {file_path}: {str(e)}")

        dictConfig(config)

        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))

    def info(self, msg, *args):
        self.logger.info(msg, *args)

    def debug(self, msg, *args):
        self.logger.debug(msg, *args)

    def warning(self, msg, *args):
        self.logger.warning(msg, *args)

    def error(self, msg, *args):
        self.logger.error(msg, *args)
