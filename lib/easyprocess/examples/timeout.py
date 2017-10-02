from easyprocess import EasyProcess

s = EasyProcess('ping localhost').call(timeout=2).stdout
print(s)
