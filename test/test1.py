#-*- coding：utf-8 -*-
import unittest
import yaml
from source.replacer.pattern import Pattern
from source.replacer.translator import Translator
from source.utilities.mclang import mclang_to_dict


class TestPattern(unittest.TestCase):

    def test_pattern(self):
        pattern_file = open('test/test1_patterns.yml', 'r', encoding='utf-8')
        pattern_content = yaml.load(pattern_file)
        pattern_list = [Pattern(x['key'], x['value'], x['token'],
                                x['repl'], x['priority']) for x in pattern_content]

        lang_file = open('test/test1.lang', 'r', encoding='utf-8')
        lang = mclang_to_dict(lang_file)
        glossary_file = open('test/test1_glossary.yml', 'r', encoding='utf-8')
        glossary = yaml.load(glossary_file)

        translator = Translator(glossary, pattern_list)

        for k, v in lang.items():
            if k == 'S:oredict.plateIron':
                self.assertEqual(translator.translate(k, v), '铁板')
            if k == 'S:oredict.plateStell':
                self.assertEqual(translator.translate(k, v), '钢板')
            if k == 'S:oredict.ingotIron':
                self.assertEqual(translator.translate(k, v), '铁锭')
            if k == 'S:oredict.ingotStell':
                self.assertEqual(translator.translate(k, v), '钢锭')


if __name__ == '__main__':
    unittest.main()
