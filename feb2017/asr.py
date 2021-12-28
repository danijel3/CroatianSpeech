import torch
import torchaudio
from datasets import Dataset
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
from pyctcdecode import build_ctcdecoder
import json
import argparse
from pathlib import Path

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='classla/wav2vec2-xls-r-parlaspeech-hr')
    parser.add_argument('--device', default='cuda', help='"cuda or "cpu"')
    parser.add_argument('--rate', type=float, default=16000)
    parser.add_argument('vad_json', type=Path)
    parser.add_argument('asr_json', type=Path)

    args = parser.parse_args()

    model_name = args.model
    device = args.device
    sampling_rate = args.rate

    with open(args.vad_json) as f:
        vad = json.load(f)

    model = Wav2Vec2ForCTC.from_pretrained(model_name).to(device)
    processor = Wav2Vec2Processor.from_pretrained(model_name)

    vocab_dict = processor.tokenizer.get_vocab()
    sorted_dict = {k.lower(): v for k, v in sorted(vocab_dict.items(), key=lambda item: item[1])}

    decoder = build_ctcdecoder(list(sorted_dict.keys()), 'lm.arpa', alpha=0.5, beta=1.0)

    files = {'sample': Path('sample.wav')}

    ds_dict = {'file': [], 'start': [], 'end': []}
    for file, ts in vad.items():
        for seg in ts:
            ds_dict['file'].append(file)
            ds_dict['start'].append(seg['start'])
            ds_dict['end'].append(seg['end'])
            ds = Dataset.from_dict(ds_dict)

    wavcache = {}


    def map_to_array(batch):
        if batch['file'] in wavcache:
            speech = wavcache[batch['file']]
        else:
            path = batch['file']
            speech, _ = torchaudio.load(path)
            speech = speech.squeeze(0).numpy()
            wavcache[batch['file']] = speech
        sstart = int(batch['start'] * sampling_rate)
        send = int(batch['end'] * sampling_rate)
        batch['speech'] = speech[sstart:send]
        return batch


    ds = ds.map(map_to_array)


    def map_to_pred_lm(batch):
        features = processor(batch["speech"], sampling_rate=sampling_rate, padding=True, return_tensors="pt")
        input_values = features.input_values.to(device)
        attention_mask = features.attention_mask.to(device)
        with torch.no_grad():
            logits = model(input_values, attention_mask=attention_mask).logits.cpu().numpy()[0]
        batch["predicted"] = decoder.decode(logits)
        return batch


    result_lm = ds.map(map_to_pred_lm, remove_columns=['speech'])

    result_lm.to_json(args.asr_json)
