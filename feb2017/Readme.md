# Corpus creating notes

Since all the files are from february 2017, the name `feb2017` was chosen.
 
List of files:

* https://www.youtube.com/watch?v=btzBgb-_Skc
* https://www.youtube.com/watch?v=IUiQxKZeT6M
* https://www.youtube.com/watch?v=6UtLzazc67o
* https://www.youtube.com/watch?v=I52pd57s6VY
* https://www.youtube.com/watch?v=COa-0-o_dbc

These where downloaded using the [yt-dlp](https://github.com/yt-dlp/yt-dlp) tool:

```
 for u in $(cat URLs) ; do yt-dlp -x --audio-format wav $u ; done
```

Next, they were all converted to 16k, mono:

```
for f in orig/*.wav ; do sox $f -r16k -c1 16k/$(basename $f) ; done
```

Following that, `vad.py` was used to generate `vad.json`.

Next `asr.py` was used to generate `asr.json` on segments found by VAD.

Finally, the `match.py` was used to match the ASR to the `ParlaMint-HR_S03.txt` file, available in [releases](https://github.com/danijel3/CroatianSpeech/releases/tag/feb2017)
creating the `matched.json` file, which contains a list of sements with the following information:
* `file` - path to the audio WAV
* `start` - start of segment within the file in seconds
* `end` - end of segment within the file in seconds
* `predicted` - output of ASR
* `human` - matched normalized human transcription