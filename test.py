from safulate.lexer import Lexer
import logging

log = logging.getLogger()
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)

s = Lexer('name + "1" + 1.25;')
print(s.start())
