import re
class XMLLibraryParser:
	def __init__(self,xmlLibrary):
		f = open(xmlLibrary)
		s = f.read()
		lines = s.split("\n")
		self.dictionary = self.parser(lines)
		
	def getValue(self,restOfLine):
		value = re.sub("<.*?>","",restOfLine)
		u = unicode(value,"utf-8")
		cleanValue = u.encode("ascii","xmlcharrefreplace")
		return cleanValue

	def keyAndRestOfLine(self,line):
		rawkey = re.search('<key>(.*?)</key>',line).group(0)
		key = re.sub("</*key>","",rawkey)
		restOfLine = re.sub("<key>.*?</key>","",line).strip()
		return key,restOfLine

	def parser(self,lines):
		dicts = 0
		songs = {}
		inSong = False
		for line in lines:
			if re.search('<dict>',line):
				dicts += 1
			if re.search('</dict>',line):
				dicts -= 1
				inSong = False
				songs[songkey] = temp
			if dicts == 2 and re.search('<key>(.*?)</key>',line):
				rawkey = re.search('<key>(.*?)</key>',line).group(0)
				songkey = re.sub("</*key>","",rawkey)
				inSong = True
				temp = {}
			if dicts == 3  and re.search('<key>(.*?)</key>',line):
				key,restOfLine = self.keyAndRestOfLine(line)
				temp[key] = self.getValue(restOfLine)
			if len(songs) > 0 and dicts < 2:
				return songs
		return songs