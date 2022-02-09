import json
import random
import string
from pathlib import Path
from typing import List, Tuple

from IPython.display import Audio
from wavio import read


def render(audio: str, segmentation: str, pfx: str):
    return f'''
<style>
    #{pfx}_container {{
        position: relative;
        height: 2rem;
        width: 100%;
        border: black 1px solid;
        border-radius: 5px;
        overflow: hidden;
    }}
    #{pfx}_container #{pfx}_progress {{
        position: absolute;
        height: 100%;
        width: 0%;
        background: hsl(200, 100%, 50%, .2);
        z-index: 2;
        pointer-events: none;
    }}
    #{pfx}_container .word {{
        color: black;
        font-size: 0.75rem;
        position: absolute;
        display: inline-flex;
        top: 0;
        height: 100%;
        z-index: 1;
        align-items: center;
        justify-content: center;
        pointer-events: none;
    }}
</style>
{audio}
<div id="{pfx}_container">
    <div id="{pfx}_progress"></div>
</div>
<script>
    let {pfx}_segmentation = {segmentation};
    let {pfx}_player = document.getElementById('{pfx}_audioplayer');
    let {pfx}_progress = document.getElementById('{pfx}_progress');
    let {pfx}_container = document.getElementById('{pfx}_container');
    let {pfx}_hue = 0;
    {pfx}_player.addEventListener('loadeddata', () => {{
        {pfx}_segmentation.forEach(el => {{
            let T = {pfx}_player.duration;
            let text = document.createElement('span');
            let start = (100 * el[1] / T);
            let end = (100 * el[2] / T);
            text.textContent = el[0];
            text.classList.add('word');
            text.style.left = start + '%';
            text.style.right = (100 - end) + '%';
            text.style.background = 'hsl(' + {pfx}_hue + ',100%,85%)';
            {pfx}_container.insertBefore(text, {pfx}_progress);
            {pfx}_hue += 50;
        }});
    }});
    setInterval(() => {{
        let p = 100.0 * {pfx}_player.currentTime / {pfx}_player.duration;
        {pfx}_progress.style.width = p + '%';
    }}, 40);
    {pfx}_container.addEventListener('click', (ev) => {{
        let p = ev.offsetX / {pfx}_container.clientWidth;
        {pfx}_player.currentTime = {pfx}_player.duration * p;
    }});
</script>
'''


def visualize(audiofile: Path, segmentation: List[Tuple[str, float, float]], sub=None):
    pfx = ''.join(random.choice(string.ascii_letters) for _ in range(6))
    if sub:
        af = read(str(audiofile))
        rate = af.rate

        samp_start = sub[0] * rate
        samp_end = sub[1] * rate

        data = af.data.flatten()[samp_start:samp_end]

        seg_filt = []
        for seg in segmentation:
            if seg[1] >= sub[0] and seg[2] <= sub[1]:
                seg_filt.append((seg[0], seg[1] - sub[0], seg[2] - sub[0]))

        audio = Audio(data=data, rate=rate)._repr_html_().replace('<audio',f'<audio id="{pfx}_audioplayer"')
        segmentation = json.dumps(seg_filt)
    else:
        audio = Audio(filename=str(audiofile))._repr_html_().replace('<audio',f'<audio id="{pfx}_audioplayer"')
        segmentation = json.dumps(segmentation)

    return render(audio, segmentation, pfx)
