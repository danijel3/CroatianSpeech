import json
import pickle
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from multiprocessing import Pool
from pathlib import Path
from struct import pack, unpack
from typing import Dict, Set, List, Tuple, Optional

from tqdm import tqdm

from hrvatski import normalize


@dataclass
class Dictionary:
    word2id: Dict[str, int] = field(default_factory=lambda: {})
    id2word: Dict[int, str] = field(default_factory=lambda: {})
    oov_token: str = '<unk>'

    def put(self, words: Set):
        for id, word in enumerate(sorted(list(words))):
            self.word2id[word] = id
            self.id2word[id] = word

    def get_id(self, word: str, warn_oov: bool = False) -> int:
        if word not in self.word2id:
            if warn_oov:
                print(f'WARN: missing word "{word}"')
            return -1
        return self.word2id[word]

    def get_word(self, id: int) -> str:
        if id == -1:
            return self.oov_token
        return self.id2word[id]

    def get_text(self, ids: List[int]) -> str:
        return ' '.join([self.get_word(x) for x in ids])

    def get_ids(self, text: str, warn_oov: bool = False) -> List[int]:
        return [self.get_id(x, warn_oov) for x in text.strip().split()]


def load_ref(file, skip_tok=False):
    lines = []
    text = []
    words = set()
    vocab = Dictionary()
    with open(file) as f:
        for l in f:
            t = l.strip()
            if skip_tok:
                t = ' '.join(t.split()[1:])
            tok = normalize(t).strip().split()
            lines.append(tok)
            words.update(tok)
        vocab.put(words)
        for l in lines:
            for w in l:
                text.append(vocab.get_id(w))
    return text, vocab


def findall(id, sequence):
    ret = []
    off = 0
    N = len(sequence)
    while off < N:
        try:
            pos = sequence.index(id, off)
            ret.append(pos)
            off = pos + 1
        except ValueError:
            break
    return ret


# def close_match(ids: List[int], text: List[int]) -> Optional[Tuple[int, int]]:
#     N = len(ids)
#     if N == 0:
#         return None
#     p1 = findall(ids[0], text)
#     poff = 1
#     while len(p1) == 0 and poff < N:
#         p2 = findall(ids[poff], text)
#         p1 = [x - poff for x in p2]
#         poff += 1
#     max_r = 0
#     pf = []
#     for p in p1:
#         sm = SequenceMatcher(a=ids, b=text[p:p + N], autojunk=False)
#         r = sm.ratio()
#         if r > max_r:
#             max_r = r
#             pf = [p]
#         elif r == max_r:
#             pf.append(p)
#
#     if len(pf) == 0:
#         # print('ERROR: no candidates found!')
#         return None
#     elif len(pf) > 1:
#         # print('WARNING: multiple candidates found!')
#         pass
#
#     pf = pf[0]
#
#     mb = SequenceMatcher(a=ids, b=text[pf:pf + N + 10], autojunk=False).get_matching_blocks()
#     m = mb[-2]
#     M = m.b + m.size
#
#     return pf, pf + M


def close_match(ids: List[int], text: List[int]) -> Optional[Tuple[int, int]]:
    N = len(ids)
    if N == 0:
        return None
    poff = 0
    cand = {}
    while poff < N:
        for x in findall(ids[poff], text):
            for s in range(x - poff - 1, x - poff + 2):
                if s not in cand:
                    cand[s] = 1
                else:
                    cand[s] += 1
        poff += 1
    if len(cand) == 0:
        return None
    L = N / 4
    if (L < 10):
        L = max(list(cand.values()))
    cand = list(dict(filter(lambda x: x[1] >= L, cand.items())).keys())
    if len(cand) == 0:
        return None
    max_r = 0
    pf = []
    for p in cand:
        sm = SequenceMatcher(a=ids, b=text[p:p + N + 10], autojunk=False)
        mb = sm.get_matching_blocks()
        if len(mb) < 2:
            continue
        M = mb[-2].b + mb[-2].size
        sm = SequenceMatcher(a=ids, b=text[p:p + M], autojunk=False)
        r = sm.ratio()
        if r > max_r:
            max_r = r
            pf = [(p, p + M)]
        elif r == max_r:
            pf.append((p, p + M))

    if len(pf) == 0:
        # print('ERROR: no candidates found!')
        return None
    elif len(pf) > 1:
        # print('WARNING: multiple candidates found!')
        pass

    return pf[0]


def init():
    global text, vocab
    with open('vocab', 'rb') as f:
        vocab = pickle.load(f)
    with open('ref.int', 'rb') as f:
        N = unpack('i', f.read(4))[0]
        text = list(unpack(f'{N}i', f.read()))


def task(seg: Dict):
    segid = vocab.get_ids(seg['predicted'])
    ret = close_match(segid, text)
    if ret is not None:
        ps, pe = ret
        seg['human'] = vocab.get_text(text[ps:pe])
    return seg


if __name__ == '__main__':

    if Path('vocab').exists() and Path('ref.int').exists():
        print('Skipping recreating reference!')
        print('Remove vocab and ref.int to recreate')
    else:
        print('Loading ref...')
        text, vocab = load_ref('ParlaMint-HR_S03.txt', skip_tok=True)
        print(f'Loaded {len(vocab.word2id)} words!')

        with open('vocab', 'wb') as f:
            pickle.dump(vocab, f)

        with open('ref.int', 'wb') as f:
            N = len(text)
            f.write(pack('i', N))
            f.write(pack(f'{N}i', *text))

    print('Counting input...')
    input = []
    with open('asr.json') as f:
        for l in f:
            input.append(json.loads(l.strip()))
    print(f'Found {len(input)} segments!')

    pool = Pool(processes=10, initializer=init)

    output = []

    with open('asr.json') as f:
        for seg in tqdm(pool.imap(task, input), total=len(input)):
            output.append(seg)

    pool.close()
    pool.join()

    print(f'Saving output...')
    with open('matched.json', 'w') as g:
        for seg in sorted(output, key=lambda x: (x['file'], x['start'])):
            g.write(json.dumps(seg) + '\n')
