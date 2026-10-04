from .aliases import (
    ALIAS_KEY, alias_target, alias_target_of_body, lookup_function
  , resolve_alias
  )
from .monadic import set_monadic_metadata
from .strings import find_static_strings
from .variables import varinfo

__all__ = [
    'ALIAS_KEY', 'alias_target', 'alias_target_of_body', 'find_static_strings'
  , 'lookup_function', 'resolve_alias', 'set_monadic_metadata', 'varinfo'
  ]

