# -*- coding: utf-8 -*-
import sys
if sys.version_info[0] < 3:
    import unicodecsv as csv
    open_kwargs = {}
else:
    import csv
    open_kwargs = {'encoding': 'utf8'}
import platform
import pytest


def assertAlmostEqual(a, b, places=3):
    assert abs(a - b) < (0.1**places)


if platform.python_implementation() == 'CPython':
    implementations = ['python', 'c']
else:
    implementations = ['python']


@pytest.fixture(params=implementations)
def jf(request):
    if request.param == 'python':
        from jellyfish import _jellyfish as jf
    else:
        from jellyfish import cjellyfish as jf
    return jf


def _load_data(name):
    with open('testdata/{}.csv'.format(name), **open_kwargs) as f:
        for data in csv.reader(f):
            yield data


@pytest.mark.parametrize("s1,s2,value", _load_data('jaro_winkler'), ids=str)
def test_jaro_winkler(jf, s1, s2, value):
    value = float(value)
    assertAlmostEqual(jf.jaro_winkler(s1, s2), value, places=3)


@pytest.mark.parametrize("s1,s2,value", _load_data('jaro_distance'), ids=str)
def test_jaro_distance(jf, s1, s2, value):
    value = float(value)
    assertAlmostEqual(jf.jaro_distance(s1, s2), value, places=3)


@pytest.mark.parametrize("s1,s2,value", _load_data('hamming'), ids=str)
def test_hamming_distance(jf, s1, s2, value):
    value = int(value)
    assert jf.hamming_distance(s1, s2) == value


@pytest.mark.parametrize("s1,s2,value", _load_data('levenshtein'), ids=str)
def test_levenshtein_distance(jf, s1, s2, value):
    value = int(value)
    assert jf.levenshtein_distance(s1, s2) == value


@pytest.mark.parametrize("s1,s2,value", _load_data('damerau_levenshtein'), ids=str)
def test_damerau_levenshtein_distance(jf, s1, s2, value):
    value = int(value)
    assert jf.damerau_levenshtein_distance(s1, s2) == value


@pytest.mark.parametrize("s1,code", _load_data('soundex'), ids=str)
def test_soundex(jf, s1, code):
    assert jf.soundex(s1) == code


@pytest.mark.parametrize("s1,code", _load_data('metaphone'), ids=str)
def test_metaphone(jf, s1, code):
    assert jf.metaphone(s1) == code


@pytest.mark.parametrize("s1,s2", _load_data('nysiis'), ids=str)
def test_nysiis(jf, s1, s2):
    assert jf.nysiis(s1) == s2


@pytest.mark.parametrize("s1,s2", _load_data('match_rating_codex'), ids=str)
def test_match_rating_codex(jf, s1, s2):
    assert jf.match_rating_codex(s1) == s2


@pytest.mark.parametrize("s1,s2,value", _load_data('match_rating_comparison'), ids=str)
def test_match_rating_comparison(jf, s1, s2, value):
    value = {'True': True, 'False': False, 'None': None}[value]
    assert jf.match_rating_comparison(s1, s2) is value


# use non-parameterized version for speed
# @pytest.mark.parametrize("a,b", _load_data('porter'), ids=str)
# def test_porter_stem(jf, a, b):
#     assert jf.porter_stem(a) == b

def test_porter_stem(jf):
    with open('testdata/porter.csv', **open_kwargs) as f:
        reader = csv.reader(f)
        for (a, b) in reader:
            assert jf.porter_stem(a) == b


if platform.python_implementation() == 'CPython':
    def test_match_rating_comparison_segfault():
        import hashlib
        from jellyfish import cjellyfish as jf
        sha1s = [u'{}'.format(hashlib.sha1(str(v).encode('ascii')).hexdigest())
                 for v in range(100)]
        # this segfaulted on 0.1.2
        assert [[jf.match_rating_comparison(h1, h2) for h1 in sha1s] for h2 in sha1s]


    def test_damerau_levenshtein_unicode_segfault():
        # unfortunate difference in behavior between Py & C versions
        from jellyfish.cjellyfish import damerau_levenshtein_distance as c_dl
        from jellyfish._jellyfish import damerau_levenshtein_distance as py_dl
        s1 = u'mylifeoutdoors'
        s2 = u'нахлыст'
        with pytest.raises(ValueError):
            c_dl(s1, s2)
        with pytest.raises(ValueError):
            c_dl(s2, s1)

        assert py_dl(s1, s2) == 14
        assert py_dl(s2, s1) == 14


def test_jaro_winkler_long_tolerance(jf):
    no_lt = jf.jaro_winkler(u'two long strings', u'two long stringz', long_tolerance=False)
    with_lt = jf.jaro_winkler(u'two long strings', u'two long stringz', long_tolerance=True)
    # make sure long_tolerance does something
    assertAlmostEqual(no_lt, 0.975)
    assertAlmostEqual(with_lt, 0.984)


def test_damerau_levenshtein_distance_type(jf):
    jf.damerau_levenshtein_distance(u'abc', u'abc')
    with pytest.raises(TypeError) as exc:
        jf.damerau_levenshtein_distance(b'abc', b'abc')
    assert 'expected' in str(exc.value)


def test_levenshtein_distance_type(jf):
    assert jf.levenshtein_distance(u'abc', u'abc') == 0
    with pytest.raises(TypeError) as exc:
        jf.levenshtein_distance(b'abc', b'abc')
    assert 'expected' in str(exc.value)


def test_jaro_distance_type(jf):
    assert jf.jaro_distance(u'abc', u'abc') == 1
    with pytest.raises(TypeError) as exc:
        jf.jaro_distance(b'abc', b'abc')
    assert 'expected' in str(exc.value)


def test_jaro_winkler_type(jf):
    assert jf.jaro_winkler(u'abc', u'abc') == 1
    with pytest.raises(TypeError) as exc:
        jf.jaro_winkler(b'abc', b'abc')
    assert 'expected' in str(exc.value)


def test_mra_comparison_type(jf):
    assert jf.match_rating_comparison(u'abc', u'abc') is True
    with pytest.raises(TypeError) as exc:
        jf.match_rating_comparison(b'abc', b'abc')
    assert 'expected' in str(exc.value)


def test_hamming_type(jf):
    assert jf.hamming_distance(u'abc', u'abc') == 0
    with pytest.raises(TypeError) as exc:
        jf.hamming_distance(b'abc', b'abc')
    assert 'expected' in str(exc.value)


def test_soundex_type(jf):
    assert jf.soundex(u'ABC') == 'A120'
    with pytest.raises(TypeError) as exc:
        jf.soundex(b'ABC')
    assert 'expected' in str(exc.value)


def test_metaphone_type(jf):
    assert jf.metaphone(u'abc') == 'ABK'
    with pytest.raises(TypeError) as exc:
        jf.metaphone(b'abc')
    assert 'expected' in str(exc.value)


def test_nysiis_type(jf):
    assert jf.nysiis(u'abc') == 'ABC'
    with pytest.raises(TypeError) as exc:
        jf.nysiis(b'abc')
    assert 'expected' in str(exc.value)


def test_mr_codex_type(jf):
    assert jf.match_rating_codex(u'abc') == 'ABC'
    with pytest.raises(TypeError) as exc:
        jf.match_rating_codex(b'abc')
    assert 'expected' in str(exc.value)


def test_porter_type(jf):
    assert jf.porter_stem(u'abc') == 'abc'
    with pytest.raises(TypeError) as exc:
        jf.porter_stem(b'abc')
    assert 'expected' in str(exc.value)
