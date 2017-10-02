from easyprocess import EasyProcess
import sys

s = EasyProcess([sys.executable, '-c', 'print "hello"']).call().stdout
print(s)
