List of files:
* https://www.youtube.com/watch?v=btzBgb-_Skc
* https://www.youtube.com/watch?v=IUiQxKZeT6M
* https://www.youtube.com/watch?v=6UtLzazc67o
* https://www.youtube.com/watch?v=I52pd57s6VY
* https://www.youtube.com/watch?v=COa-0-o_dbc

```
 for u in $(cat URLs) ; do yt-dlp -x --audio-format wav $u ; done
```

Converted all the files to 16k, mono:
```
for f in orig/*.wav ; do sox $f -r16k -c1 16k/$(basename $f) ; done
```
