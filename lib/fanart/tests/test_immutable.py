from unittest import TestCase
from fanart.immutable import Immutable


class TestMutable(object):
    def __init__(self, spam, ham, eggs):
        self.spam = spam
        self.ham = ham
        self.eggs = eggs

    @Immutable.mutablemethod
    def anyway(self):
        self.spam = self.ham + self.eggs


class TestImmutable(TestMutable, Immutable):
    @Immutable.mutablemethod
    def __init__(self, *args, **kwargs):
        super(TestImmutable, self).__init__(*args, **kwargs)


class ImmutableTestCase(TestCase):
    def setUp(self):
        self.instance = TestImmutable('spam', 'ham', 'eggs')

    def test_set_raises(self):
        self.assertRaises(TypeError, self.instance.__setattr__, 'spam', 'ham')

    def test_set(self):
        self.instance._mutable = True
        self.instance.spam = 'ham'
        self.assertEqual(self.instance.spam, 'ham')

    def test_del_raises(self):
        self.assertRaises(TypeError, self.instance.__delattr__, 'spam')

    def test_del(self):
        self.instance._mutable = True
        del self.instance.spam
        self.assertRaises(AttributeError, self.instance.__getattribute__, 'spam')

    def test_equal(self):
        new_instance = TestImmutable('spam', 'ham', 'eggs')
        self.assertEqual(self.instance, new_instance)

    def test_mutable_dec(self):
        instance = TestMutable('spam', 'ham', 'eggs')
        instance.anyway()
        self.assertEqual(instance.spam, 'hameggs')
