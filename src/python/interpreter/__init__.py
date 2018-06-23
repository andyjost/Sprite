from ..exceptions import *
import logging
import os

__all__ = ['Interpreter']

# Logging setup.
# ==============
logger = logging.getLogger(__name__)
LOG_LEVELS = {k:getattr(logging, k)
    for k in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
  }
DEFAULT_LOG_LEVEL = 'ERROR'
LOG_FILE = os.environ.get('SPRITE_LOG_FILE', '-')
logging.basicConfig(
    level=LOG_LEVELS[
        os.environ.get('SPRITE_LOG_LEVEL', DEFAULT_LOG_LEVEL).upper()
      ]
  , format='%(asctime)s [%(levelname)s] %(message)s'
  , datefmt='%m/%d/%Y %H:%M:%S'
  , **({'filename': LOG_FILE} if LOG_FILE not in ['-', ''] else {})
  )

del logging
del os

from .interpreter import Interpreter
