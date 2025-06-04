from . import interpreter as interpreter
from . import lexer as lexer
from . import parser as parser
from ._version import __version__ as __version__
from .errors import *

from .interpreter.repl import run_code as run_code, run_file as run_file