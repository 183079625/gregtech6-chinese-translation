# GT6-Translation RegexReplacer.py
# by Tanimodori GPL v3.0

import sys
import datetime
import codecs
import re
import os.path
import json
import argparse
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())  # utf-8 output

# Init a parser
_parser = argparse.ArgumentParser(
    description='A simple regex-based replacer dealt with GregTech6 Chinese Translasion')
_parser.add_argument('-d', '--delobs', action='store_true', default=False,
                     help='To delete item only exist in translated file')
_parser.add_argument('-r', '--respect', action='store_true', default=False,
                     help='To use translated translations instead of the processed ones')
_parser.add_argument('-p', '--partial', action='store_true', default=False,
                     help='To allow unknown main word in translation')
_parser.add_argument(
    'translated', help='The path of currently translated GregTech.lang')
_parser.add_argument('original', help='The path of original GregTech.lang')
_parser.add_argument(
    'glossary', help='The path of glossary, auto-create if not exist')
_parser.add_argument('pattern', help='The path of regex patterns')
_parser.add_argument('output', help='The path of output GregTech.lang')
_parser.add_argument('exception', help='The path of exceptions of entries')
_parser.add_argument('-t', '--track', nargs='+',
                     help='Regex expressions of which subject you want to track')
_args = _parser.parse_args()

# Settings
path_of_translated = _args.translated
path_of_original = _args.original
path_of_output = _args.output
path_of_glossary = _args.glossary
path_of_pattern = _args.pattern
path_of_exception = _args.exception
delete_obsolete_item = _args.delobs
respect_translated = _args.respect
allow_partial_translation = _args.partial
track_regs = _args.track


class pattern:
    def __init__(self, name, value, repl, priority=-1):
        self.name = name
        self.name_reg = re.compile(name)
        self.value = value
        self.value_reg = re.compile(value)
        self.repl = repl
        self.priority = priority

    #@classmethod
    # def cleanupGlossary(cls):

    @classmethod
    def loadFile(cls, path):
        ret = []
        with open(path, 'r', encoding='utf-8') as f:
            arr = json.loads(f.read())
            if len(arr) > 0:
                for item in arr:
                    ret.append(pattern(item['name'], item['value'],
                                       item['repl'], item['priority']))
        return ret


class ExceptingEntries:
    def __init__(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            self.entries = json.loads(f.read())


class LangItem:
    def __init__(self, key, en='', zh=''):
        self.key = key
        self.en = en
        self.zh_old = zh
        self.zh_new = zh


class LangItemCollection:
    def __init__(self, original, translated):
        """Store original and translated in one sorted dict"""
        self.items = {}
        self.loadFile(path_of_original, True)
        self.loadFile(path_of_translated, False)
        sorted(self.items.items(), key=lambda x: x[0])

    def loadFile(self, path, isoriginal):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('S:'):
                    line_list = line.split("=", 1)
                    k = line_list[0][2:]
                    v = line_list[1]
                    if k not in self.items:
                        if (not isoriginal) and delete_obsolete_item:
                            continue
                        self.items[k] = LangItem(k, '', '')
                    if isoriginal:
                        self.items[k].en = v
                    else:
                        self.items[k].zh_old = v

    def process(self, patterns, glossary, excepting_entries, tracking=None, log_file=None):
        """Process this LangItemCollection with given partterns and glossary"""
        if tracking is not None:
            # Debug info
            _tracking_regs = []
            for _s in tracking:
                try:
                    _r = re.compile(_s)
                    _tracking_regs.append(_r)
                except:
                    log_file.write(
                        '[ERROR] Invalid regex {0}, skipping...\n'.format(_s))
        if tracking is None or len(_tracking_regs) == 0:
            _tracking_regs = None
            _tracking_current = False

        for _item in self.items.values():
            if _tracking_regs is not None:
                # Judge if should track
                _tracking_current = any(
                    [x.match(_item.key) is not None for x in _tracking_regs])

            # Invalid items or items that needn't process
            if (_item.en == '' and delete_obsolete_item) or (_item.zh_old != ''and _item.zh_old != _item.en and respect_translated):
                if _tracking_current:
                    # Debug info
                    log_file.write('[Warning] Invalid entry {0}:{1}/{2}, respect_translated={3}, skipping...\n'.format(
                        _item.key, _item.en, _item.zh_old, respect_translated))
                _item.zh_new=_item.zh_old
                continue
            # Excepting entries
            if _item.key in excepting_entries.entries:
                _item.zh_new = excepting_entries.entries[_item.key]
                if _tracking_current:
                    # Debug info
                    log_file.write('[Excepting] Entry {0}:{1}/{2}->{3}, skipping...\n'.format(
                        _item.key, _item.en, _item.zh_old, _item.zh_new))
                continue
            # Search for patterns whose 'name' matches item.en
            # Order by priority in desending
            _patterns_to_be_processd = sorted(filter(lambda x: x.name_reg.match(
                _item.key) is not None, patterns), key=lambda x: x.priority, reverse=True)
            _item.main_word_en = _item.en
            # If have any matched pattern's name
            if len(_patterns_to_be_processd) > 0:
                if _tracking_current:
                    log_file.write('[Info] {0} regex(es) matched the name of entry {1}:{2}\n'.format(
                        len(_patterns_to_be_processd), _item.key, _item.en))
                # Init a stack for item
                _item.pattern_stack = []
                for _p in _patterns_to_be_processd:
                    # Match the pattern's value
                    _matched = _p.value_reg.match(_item.main_word_en)
                    if _matched is not None and 'mw' in _matched.groupdict():
                        if _tracking_current:
                            log_file.write('[Matched] {0}->{1}, main word: {2}->{3}\n'.format(
                                _p.value, _p.repl, _item.main_word_en, _matched.group('mw')))
                        # Value matched
                        _item.pattern_stack.append(_p)
                        # Set next main word
                        _item.main_word_en = _matched.group('mw')
                    else:
                        if _tracking_current:
                            log_file.write(
                                '[Failed] {0}->{1}\n'.format(_p.value, _p.repl))
                # Get the main word from the glossary
                _item.main_word_zh = glossary.get_main_word(
                    _item.main_word_en, _item.key)
                if _item.main_word_zh is None:
                    # No available translation of this glossary
                    # TODO add a debug info
                    if allow_partial_translation:
                        if _tracking_current:
                            log_file.write(
                                '[Partial] Using a partial main word {0}\n'.format(_item.main_word_en))
                        # Using partial translation
                        _item.main_word_zh = _item.main_word_en
                    else:
                        if _tracking_current:
                            log_file.write('[Failed] No matching main word of {0}, using original.\n'.format(
                                _item.main_word_en))
                        # Using the original
                        _item.zh_new = _item.zh_old
                        # Next item
                        continue
                if _tracking_current:
                    log_file.write(
                        '[Found] Using main word {0}->{1}\n'.format(_item.main_word_en, _item.main_word_zh))
                # Have available or partial translation
                _item.zh_new = _item.main_word_zh
                # Replace in a reserved order
                for _p in _item.pattern_stack[::-1]:
                    _item.zh_new = _p.repl.format(_item.zh_new)
                if _tracking_current:
                    log_file.write('[Result] The entry {0} is processed: {1}/{2}->{3}\n'.format(
                        _item.key, _item.en, _item.zh_old, _item.zh_new))
            else:
                if _tracking_current:
                    # Debug info
                    log_file.write(
                        '[Info] No regex matched the name of entry {0}\n'.format(_item.key))
                # No matched patterns
                _item.zh_new = _item.zh_old
            if _tracking_current:
                log_file.write('[Result] The entry {0} is processed: {1}/{2}->{3}\n'.format(
                    _item.key, _item.en, _item.zh_old, _item.zh_new))

    def save_to(self, path):
        """Save this langFile to a given path"""
        with open(path, 'w', encoding='utf-8') as f:
            # Writes heading
            #f.write(
            #    '# Configuration file\n\nenablelangfile {\n    B:UseThisFileAsLanguageFile=true\n}\n\n\nlanguagefile {\n')
            # Sort in the order of keys
            for _item in sorted(self.items.values(), key=lambda x: x.key):
                f.write('S:{0}={1}\n'.format(_item.key, _item.zh_new))
            # Writes ending
            #f.write('}\n\n\n')

# TODO
# class PatternItem:
#    def __init__(self,name,value,repl,priority):
#        self.name=name
#        self.value=value
#        self.repl=repl
#        self.priority=priority
#
# class PatternCollection:
#    pass


class Glossary:
    def __init__(self, file_path):
        if os.path.isfile(path_of_glossary):
            try:
                with open(path_of_glossary, 'r', encoding='utf-8') as f:
                    self.items = json.load(f)
            except:
                self.items = {}
        else:
            self.items = {}

    def save_to(self, file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.items, f, ensure_ascii=False,
                      sort_keys=True, indent=4)

    def get_main_word(self, word, key):
        if word not in self.items:
            return None
        obj = self.items[word]
        if type(obj) is str:
            return obj
        else:
            fallback = None
            for k, v in obj.items():
                if k == '.*':
                    fallback = v
                    continue
                if re.match(k, key):
                    return v
            return fallback


if __name__ == '__main__':
    # Load File
    _lang = LangItemCollection(path_of_original, path_of_translated)
    _p = pattern.loadFile(path_of_pattern)
    _g = Glossary(path_of_glossary)
    _ee = ExceptingEntries(path_of_exception)
    if track_regs is not None and len(track_regs) > 0:
        # Save log to the directory of this program
        log_path = sys.path[0] + '/' + (datetime.datetime.utcnow().isoformat(
            sep='-', timespec='seconds').replace(':', '-')) + '.log'
        with open(log_path, 'w', encoding='utf-8') as _f:
            _lang.process(_p, _g, _ee, tracking=track_regs, log_file=_f)
    else:
        _lang.process(_p, _g, _ee)
    _lang.save_to(path_of_output)
    _g.save_to(path_of_glossary)
