from easyprocess import EasyProcess
import sys

v = EasyProcess([sys.executable, '--version']).call().stderr
print('your python version:%s' % v)
