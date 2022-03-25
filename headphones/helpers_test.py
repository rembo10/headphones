# -*- coding: utf-8 -*-
from .unittestcompat import TestCase
from headphones.helpers import clean_name, is_valid_date, age


class HelpersTest(TestCase):

    def test_clean_name(self):
        """helpers: check correctness of clean_name() function"""
        cases = {
            ' Weiße & rose ': 'Weisse and rose',
            'Multiple / spaces': 'Multiple spaces',
            'Kevin\'s m²': 'Kevins m2',
            'Symphonęy Nº9': 'Symphoney No.9',
            'ÆæßðÞĲĳ': 'AeaessdThIJıj',
            'Obsessió (Cerebral Apoplexy remix)': 'obsessio cerebral '
                                                    'apoplexy remix',
            'Doktór Hałabała i siedmiu zbojów': 'doktor halabala i siedmiu '
                                                    'zbojow',
            'Arbetets Söner och Döttrar': 'arbetets soner och dottrar',
            'Björk Guðmundsdóttir': 'bjork gudmundsdottir',
            'L\'Arc~en~Ciel': 'larc en ciel',
            'Orquesta de la Luz (オルケスタ・デ・ラ・ルス)':
                'Orquesta de la Luz オルケスタ デ ラ ルス'

        }
        for first, second in cases.items():
            nf = clean_name(first).lower()
            ns = clean_name(second).lower()
            self.assertEqual(
                nf, ns, "check cleaning of case (%s,"
                        "%s)" % (nf, ns)
            )

    def test_clean_name_nonunicode(self):
        """helpers: check if clean_name() works on non-unicode input"""
        input = 'foo $ bar/BAZ'
        test = clean_name(input).lower()
        expected = 'foo bar baz'
        self.assertEqual(
            test, expected, "check clean_name() works on non-unicode"
        )
        input = 'fóó $ BAZ'
        test = clean_name(input).lower()
        expected = clean_name('%fóó baz ').lower()
        self.assertEqual(
            test, expected, "check clean_name() with narrow non-ascii input"
        )

    def test_is_valid_date(date):
        test_cases = [
            ('2021-11-12', True, "check is_valid_date returns True for valid date"),
            (None, False, "check is_valid_date returns False for None"),
            ('2021-11', False, "check is_valid_date returns False for incomplete"),
            ('2021', False, "check is_valid_date returns False for incomplete")
        ]
        for input, expected, desc in test_cases:
            self.assertEqual(is_valid_date(input), expected, desc)
