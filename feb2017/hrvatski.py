from enum import Enum
from typing import List

from tqdm import tqdm

from strings_hr import abbreviations, sym_ignore, symbols, number_to_text

print_abbrev = False

WordType = Enum('WordType', 'unknown ignore word number time abbreviation symbol')


class Word:
    def __init__(self, text, type=WordType.unknown):
        self.text = text
        self.type = type
        self.subwords = None
        self.space = False

    @staticmethod
    def fromSubwords(subwords, type=WordType.unknown):
        text = ''.join([x.text for x in subwords])
        ret = Word(text, type)
        ret.subwords = subwords
        ret.space = subwords[-1].space
        return ret

    def verbalize(self):

        text = self.text.lower()

        if self.type == WordType.ignore:
            text = ''

        if self.type == WordType.symbol:
            text = symbols[self.text]

        if self.type == WordType.abbreviation:
            if self.text in abbreviations:
                text = abbreviations[self.text]

        if self.type == WordType.number:
            text = number_to_text(int(self.text))

        if self.type == WordType.time:
            text = f'{number_to_text(int(self.subwords[0].text))} i {number_to_text(int(self.subwords[2].text))}'

        T = {
            WordType.unknown: '??:'
        }.get(self.type, '')

        sp = ''
        if self.space:
            sp = ' '

        return f'{T}{text}{sp}'

    def __repr__(self):
        T = {
            WordType.unknown: '??:',
            WordType.ignore: '@I:',
            WordType.word: '@W:',
            WordType.number: '@N:',
            WordType.date: '@D:',
            WordType.time: '@T:',
            WordType.currency: '@C:',
            WordType.abbreviation: '@A:',
            WordType.symbol: '@S:'
        }.get(self.type, '')

        return f'{T}{self.text}'


def divide(text: str) -> List[str]:
    # Split string into substrings containing one class of alpha/numeric/other
    # exception is periods which can repeat
    ret = []
    tx = ''
    lt = -1
    ns = False
    for c in text:
        if c.isalpha():
            tt = 0
        elif c.isnumeric():
            tt = 1
        else:
            tt = 2
            if c == '.' and tx and tx[-1] == '.':
                ns = False
            else:
                ns = True
        if tt != lt or ns:
            if tx:
                ret.append(tx)
            tx = ''
            lt = tt
            ns = False
        tx = tx + c
    if tx:
        ret.append(tx)
    return ret


def classify(text: str) -> List[Word]:
    tokens = text.strip().split()

    ret = []
    for tok in tokens:
        d = divide(tok)
        for st in d:

            T = WordType.unknown
            if st[0].isdigit():
                T = WordType.number
            elif st in abbreviations:
                T = WordType.abbreviation
            elif st[0].isalpha():
                T = WordType.word
            elif st in sym_ignore:
                T = WordType.ignore
            elif st in symbols:
                T = WordType.symbol

            word = Word(st, T)
            word.space = False
            ret.append(word)
        ret[-1].space = True

    return ret


def check_upper(text: str) -> bool:  # check if more than one uppercase letter in word
    u = 0
    for c in text:
        if c.isupper():
            u += 1
            if u > 1:
                return True
    return False


abbrev_words = set()


def analyze_abbrev(words):
    for i, word in enumerate(words):
        if check_upper(word.text):
            abbrev_words.add(word.text)
        if word.type == WordType.word and i < len(words) - 2:
            if words[i + 1].text == '.' and words[i + 2].text[0].islower():
                abbrev_words.add(word.text)
        if word.type == WordType.word:
            vowel = False
            for c in word.text.lower():
                if c in ['a', 'e', 'i', 'o', 'u']:
                    vowel = True
                    break
            if not vowel:
                abbrev_words.add(word.text)


def check_time(words: List[Word]) -> bool:
    if words[0].type == WordType.number and words[2].type == WordType.number and len(words[0].text) <= 2 and \
            len(words[2].text) == 2 and words[1].text in [':', ',']:
        return True
    else:
        return False


def join(words: List[Word]) -> List[Word]:
    ret = []
    while words:
        if len(words) >= 3 and check_time(words[:3]):
            sw = words[:3]
            words = words[3:]
            ret.append(Word.fromSubwords(sw, WordType.time))
        elif len(words) > 1 and words[0].type == WordType.number and words[1].type == WordType.number:
            sw = []
            while len(words) > 0 and words[0].type == WordType.number:
                sw.append(words.pop(0))
            ret.append(Word.fromSubwords(sw, WordType.number))
        else:
            ret.append(words.pop(0))
    return ret


def normalize(text: str) -> str:
    words = classify(text)
    words = join(words)
    if print_abbrev:
        analyze_abbrev(words)
    words = [w.verbalize() for w in words]
    return ''.join(filter(None, words))  # join, but skip empty string


if __name__ == '__main__':
    words = set()
    with open('text') as f, open('normalized', 'w') as g:
        for l in f:
            i = l.find(' ')
            text = ''
            if i < 0:
                uid = l.strip()
            else:
                uid = l[:i].strip()
                text = l[i + 1:].strip()
            text = normalize(text)
            g.write(f'{uid} {text}\n')
            words.update(text.split())

    with open('wordlist', 'w') as h:
        for w in sorted(words):
            h.write(f'{w}\n')
