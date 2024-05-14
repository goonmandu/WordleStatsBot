import os
from enum import Enum


# Exit Codes
# Anything thrown under OTHER_ERR should be diagnosed and reported in a future patch.
class ExitCode(Enum):
    INVALID_JSON_FILE = 1
    OTHER_ERR         = 2
