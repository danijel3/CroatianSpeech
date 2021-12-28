import torch
import json
import argparse
from pathlib import Path
from math import ceil


def resample(ts, max_gap=3, max_len=30):
    new_ts = []
    for s in ts:
        if s['end'] - s['start'] > max_len:
            print(f'Error: max_len ({max_len}) is smaller than one of the segments ({s})!')
            L = s['end'] - s['start']
            N = ceil(L / max_len)
            P = L / N
            for p in range(N - 1):
                ss = s['start'] + p * P
                new_ts.append({'start': ss, 'end': ss + P})
                print(f'Added {new_ts[-1]}')
            new_ts.append({'start': s['start'] + (N - 1) * P, 'end': s['end']})
            print(f'Added {new_ts[-1]}')
        else:
            new_ts.append(s)
    ts = new_ts
    gts = []
    g = [ts[0]]
    for s in ts[1:]:
        if s['start'] - g[-1]['end'] < max_gap:
            g.append(s)
        else:
            gts.append(g)
            g = [s]
    gts.append(g)
    ret = []
    for g in gts:
        l = g[-1]['end'] - g[0]['start']
        split_num = ceil(l / max_len)
        if split_num > 1:
            min_len = l / split_num
            start = g[0]['start']
            end = g[0]['end']
            for s in g[1:]:
                if s['end'] - start > max_len or end - start > min_len:
                    ret.append({'start': start, 'end': end})
                    start = s['start']
                    end = s['end']
                else:
                    end = s['end']
            ret.append({'start': start, 'end': end})
        else:
            ret.append({'start': g[0]['start'], 'end': g[-1]['end']})
    return ret


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--rate', type=float, default=16000)
    parser.add_argument('--padding', type=int, default=1000)
    parser.add_argument('vad_json', type=Path)
    parser.add_argument('input_wav', nargs='+', type=Path)

    args = parser.parse_args()

    rate = args.rate
    padding = args.padding

    vad_model, vad_utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                          model='silero_vad',
                                          force_reload=True)

    (get_speech_timestamps,
     save_audio,
     read_audio,
     VADIterator,
     collect_chunks) = vad_utils

    output = {}

    for file in args.input_wav:
        print(f'Processing {file}...')
        wav = read_audio(str(file), sampling_rate=rate)
        vad_ts = get_speech_timestamps(wav, vad_model, sampling_rate=rate, speech_pad_ms=padding, return_seconds=True)
        ts = resample(vad_ts)
        print(f'Found {len(ts)} segments.')
        output[str(file)] = ts

    with open(args.vad_json, 'w') as f:
        json.dump(output, f)
