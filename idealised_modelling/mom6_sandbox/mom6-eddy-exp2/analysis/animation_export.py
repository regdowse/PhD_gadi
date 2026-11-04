"""Save a Matplotlib JSHTML animation with embedded frames and offline controls."""
from html import escape
from pathlib import Path
import re


def save_animation_html(animation_html, directory, experiment_name, segment):
    """Write a standalone HTML player beside its notebook; return its path."""
    if not animation_html.strip():
        raise ValueError('Render the animation before saving it.')
    if re.search(r'<script\b[^>]*\bsrc=', animation_html, flags=re.IGNORECASE):
        raise ValueError('Animation has an external script and cannot be exported offline.')
    # JSHTML embeds the frames/JavaScript but normally links Font Awesome icons.
    # Replace that stylesheet with local Unicode icons for offline playback.
    player = re.sub(r'<link\b[^>]*>', '', animation_html, flags=re.IGNORECASE)
    icons = {'fa-fast-backward':'⏮', 'fa-step-backward':'◀|',
             'fa-play':'▶', 'fa-pause':'❚❚', 'fa-step-forward':'|▶',
             'fa-fast-forward':'⏭', 'fa-minus':'−', 'fa-plus':'+'}
    icon_css = ''.join(f'.{name}::before {{content: "{symbol}";}}'
                       for name, symbol in icons.items())
    style = ('.fa {font-family: sans-serif; font-style: normal; display: inline-block;}'
             '.fa-flip-horizontal {transform: scaleX(-1);}' + icon_css)
    clean = lambda value: re.sub(r'[^A-Za-z0-9_.-]+', '_', str(value)).strip('._') or 'animation'
    title = escape(f'{experiment_name} / {segment} — eddy animation')
    target = Path(directory) / f'{clean(experiment_name)}_{clean(segment)}_eddy_animation.html'
    document = (f'<!DOCTYPE html>\n<html><head><meta charset="utf-8">'
                f'<title>{title}</title><style>{style}</style></head>'
                f'<body>{player}</body></html>\n')
    target.write_text(document, encoding='utf-8')
    return target
