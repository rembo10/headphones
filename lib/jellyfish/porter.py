from .compat import _range

_s2_options = {
    'a': ((['a', 't', 'i', 'o', 'n', 'a', 'l'], ['a', 't', 'e']),
          (['t', 'i', 'o', 'n', 'a', 'l'], ['t', 'i', 'o', 'n'])),
    'c': ((['e', 'n', 'c', 'i'], ['e', 'n', 'c', 'e']),
          (['a', 'n', 'c', 'i'], ['a', 'n', 'c', 'e']),),
    'e': ((['i', 'z', 'e', 'r'], ['i', 'z', 'e']),),
    'l': ((['b', 'l', 'i'], ['b', 'l', 'e']),
          (['a', 'l', 'l', 'i'], ['a', 'l']),
          (['e', 'n', 't', 'l', 'i'], ['e', 'n', 't']),
          (['e', 'l', 'i'], ['e']),
          (['o', 'u', 's', 'l', 'i'], ['o', 'u', 's']),),
    'o': ((['i', 'z', 'a', 't', 'i', 'o', 'n'], ['i', 'z', 'e']),
          (['a', 't', 'i', 'o', 'n'], ['a', 't', 'e']),
          (['a', 't', 'o', 'r'], ['a', 't', 'e']),),
    's': ((['a', 'l', 'i', 's', 'm'], ['a', 'l']),
          (['i', 'v', 'e', 'n', 'e', 's', 's'], ['i', 'v', 'e']),
          (['f', 'u', 'l', 'n', 'e', 's', 's'], ['f', 'u', 'l']),
          (['o', 'u', 's', 'n', 'e', 's', 's'], ['o', 'u', 's']),),
    't': ((['a', 'l', 'i', 't', 'i'], ['a', 'l']),
          (['i', 'v', 'i', 't', 'i'], ['i', 'v', 'e']),
          (['b', 'i', 'l', 'i', 't', 'i'], ['b', 'l', 'e']),),
    'g': ((['l', 'o', 'g', 'i'], ['l', 'o', 'g']),),
}


_s3_options = {
    'e': ((['i', 'c', 'a', 't', 'e'], ['i', 'c']),
          (['a', 't', 'i', 'v', 'e'], []),
          (['a', 'l', 'i', 'z', 'e'], ['a', 'l']),),
    'i': ((['i', 'c', 'i', 't', 'i'], ['i', 'c']),),
    'l': ((['i', 'c', 'a', 'l'], ['i', 'c']),
          (['f', 'u', 'l'], []),),
    's': ((['n', 'e', 's', 's'], []),),
}

_s4_endings = {
    'a': (['a', 'l'],),
    'c': (['a', 'n', 'c', 'e'], ['e', 'n', 'c', 'e']),
    'e': (['e', 'r'],),
    'i': (['i', 'c'],),
    'l': (['a', 'b', 'l', 'e'], ['i', 'b', 'l', 'e']),
    'n': (['a', 'n', 't'], ['e', 'm', 'e', 'n', 't'], ['m', 'e', 'n', 't'],
          ['e', 'n', 't']),
    # handle 'o' separately
    's': (['i', 's', 'm'],),
    't': (['a', 't', 'e'], ['i', 't', 'i']),
    'u': (['o', 'u', 's'],),
    'v': (['i', 'v', 'e'],),
    'z': (['i', 'z', 'e'],),
}


class Stemmer(object):
    def __init__(self, b):
        self.b = list(b)
        self.k = len(b)-1
        self.j = 0

    def cons(self, i):
        """ True iff b[i] is a consonant """
        if self.b[i] in 'aeiou':
            return False
        elif self.b[i] == 'y':
            return True if i == 0 else not self.cons(i-1)
        return True

    def m(self):
        n = i = 0
        while True:
            if i > self.j:
                return n
            if not self.cons(i):
                break
            i += 1
        i += 1
        while True:
            while True:
                if i > self.j:
                    return n
                if self.cons(i):
                    break
                i += 1

            i += 1
            n += 1

            while True:
                if i > self.j:
                    return n
                if not self.cons(i):
                    break
                i += 1
            i += 1

    def vowel_in_stem(self):
        """ True iff 0...j contains vowel """
        for i in _range(0, self.j+1):
            if not self.cons(i):
                return True
        return False

    def doublec(self, j):
        """ True iff j, j-1 contains double consonant """
        if j < 1 or self.b[j] != self.b[j-1]:
            return False
        return self.cons(j)

    def cvc(self, i):
        """ True iff i-2,i-1,i is consonent-vowel consonant
        and if second c isn't w,x, or y.
        used to restore e at end of short words like cave, love, hope, crime
        """
        if (i < 2 or not self.cons(i) or self.cons(i-1) or not self.cons(i-2) or
                self.b[i] in 'wxy'):
            return False
        return True

    def ends(self, s):
        length = len(s)
        """ True iff 0...k ends with string s """
        res = (self.b[self.k-length+1:self.k+1] == s)
        if res:
            self.j = self.k - length
        return res

    def setto(self, s):
        """ set j+1...k to string s, readjusting k """
        length = len(s)
        self.b[self.j+1:self.j+1+length] = s
        self.k = self.j + length

    def r(self, s):
        if self.m() > 0:
            self.setto(s)

    def step1ab(self):
        if self.b[self.k] == 's':
            if self.ends(['s', 's', 'e', 's']):
                self.k -= 2
            elif self.ends(['i', 'e', 's']):
                self.setto(['i'])
            elif self.b[self.k-1] != 's':
                self.k -= 1
        if self.ends(['e', 'e', 'd']):
            if self.m() > 0:
                self.k -= 1
        elif ((self.ends(['e', 'd']) or self.ends(['i', 'n', 'g'])) and
              self.vowel_in_stem()):
            self.k = self.j
            if self.ends(['a', 't']):
                self.setto(['a', 't', 'e'])
            elif self.ends(['b', 'l']):
                self.setto(['b', 'l', 'e'])
            elif self.ends(['i', 'z']):
                self.setto(['i', 'z', 'e'])
            elif self.doublec(self.k):
                self.k -= 1
                if self.b[self.k] in 'lsz':
                    self.k += 1
            elif self.m() == 1 and self.cvc(self.k):
                self.setto(['e'])

    def step1c(self):
        """ turn terminal y into i if there's a vowel in stem """
        if self.ends(['y']) and self.vowel_in_stem():
            self.b[self.k] = 'i'

    def step2and3(self):
        for end, repl in _s2_options.get(self.b[self.k-1], []):
            if self.ends(end):
                self.r(repl)
                break

        for end, repl in _s3_options.get(self.b[self.k], []):
            if self.ends(end):
                self.r(repl)
                break

    def step4(self):
        ch = self.b[self.k-1]

        if ch == 'o':
            if not ((self.ends(['i', 'o', 'n']) and self.b[self.j] in 'st') or
                    self.ends(['o', 'u'])):
                return
        else:
            endings = _s4_endings.get(ch, [])
            for end in endings:
                if self.ends(end):
                    break
            else:
                return

        if self.m() > 1:
            self.k = self.j

    def step5(self):
        self.j = self.k
        if self.b[self.k] == 'e':
            a = self.m()
            if a > 1 or a == 1 and not self.cvc(self.k-1):
                self.k -= 1
        if self.b[self.k] == 'l' and self.doublec(self.k) and self.m() > 1:
            self.k -= 1

    def result(self):
        return ''.join(self.b[:self.k+1])

    def stem(self):
        if self.k > 1:
            self.step1ab()
            self.step1c()
            self.step2and3()
            self.step4()
            self.step5()
        return self.result()
