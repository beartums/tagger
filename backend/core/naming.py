"""Rename templates -> sanitized relative paths."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_CONTROL = re.compile(r'[\x00-\x1f]')

# Lidarr's colon options (Settings → Media Management → Colon Replacement).
COLONS = {
    "delete": "",
    "dash": "-",
    "space_dash": " -",
    "space_dash_space": " - ",
    "smart": None,          # ": " → " - ", any other ":" → "-"
}

# Lidarr's "Replace Illegal Characters" (FileNameBuilder.CleanFileName).
_ILLEGAL = [("\\", "+"), ("/", "+"), ("<", ""), (">", ""), ("?", "!"), ("*", "-"), ("|", ""), ('"', "")]


@dataclass(frozen=True)
class NamingRules:
    """How characters in a tag value become a file or folder name; defaults match Lidarr's."""
    replace_illegal: bool = True
    colon: str = "smart"

    @classmethod
    def from_settings(cls, s) -> "NamingRules":
        colon = s.naming_colon if s.naming_colon in COLONS else "smart"
        return cls(replace_illegal=s.naming_replace_illegal, colon=colon)


def current_rules() -> NamingRules:
    from api.config import _load
    return NamingRules.from_settings(_load())


def clean_value(value: str, rules: NamingRules = NamingRules()) -> str:
    """
    One tag value as Lidarr would write it into a name: colons per the colon
    setting, then / \\ ? * < > | " replaced (or deleted with replacement off).
    A "/" in a value therefore never makes a folder ("AC/DC" → "AC+DC").
    """
    if rules.replace_illegal:
        if rules.colon == "smart":
            value = value.replace(": ", " - ").replace(":", "-")
        else:
            value = value.replace(":", COLONS[rules.colon])
    else:
        value = value.replace(":", "")
    for bad, good in _ILLEGAL:
        value = value.replace(bad, good if rules.replace_illegal else "")
    return _CONTROL.sub("_", value)


def _safe(part: str) -> str:
    """Sanitize a single path component."""
    part = _UNSAFE.sub('_', part).strip('. ')
    return part or '_'


def safe_name(name: str, rules: NamingRules = NamingRules()) -> str:
    """A single file or folder name typed by hand, cleaned like a tag value."""
    return _safe(clean_value(name, rules))


# Lidarr's "{Artist NameThe}": a leading article moves to the end, before any
# trailing "(...)" -- "The Pogues" -> "Pogues, The", "A Band (UK)" -> "Band, A (UK)".
_ARTICLE = re.compile(r'^(The|An|A) (.*?)((?: *\([^)]+\))*)$', re.IGNORECASE)


def _the(s: str) -> str:
    m = _ARTICLE.match(s)
    return f"{m.group(2)}, {m.group(1)}{m.group(3)}" if m and m.group(2) else s


def render_template(template: str, tags: dict, ext: str, rules: NamingRules = NamingRules()) -> str:
    """
    Render a rename template into a sanitized path relative to the track's library root,
    with the given extension. Raises ValueError/KeyError on a bad template.
    {artist_the}, {album_artist_the} and {album_the} are the "Name, The" forms.
    Each value is cleaned on its own (clean_value), so only the template's own
    "/" makes folders; each resulting name then loses leading/trailing dots and
    spaces (a trailing dot isn't allowed over SMB, though Lidarr keeps it).
    """
    fields = {
        'title':        tags.get('title') or '',
        'artist':       tags.get('artist') or '',
        'album':        tags.get('album') or '',
        'album_artist': tags.get('album_artist') or tags.get('artist') or '',
        'year':         tags.get('year') or '',
        'genre':        tags.get('genre') or '',
        'track_number': tags.get('track_number') or '0',
        'disc_number':  tags.get('disc_number') or '0',
    }
    track_num = int(re.sub(r'\D.*', '', fields['track_number']) or '0')
    disc_num  = int(re.sub(r'\D.*', '', fields['disc_number'])  or '0')
    text = ('title', 'artist', 'album', 'album_artist', 'year', 'genre')
    rel = template.format(
        track_number=track_num,
        disc_number=disc_num,
        **{k: clean_value(fields[k], rules) for k in text},
        **{f"{k}_the": clean_value(_the(fields[k]), rules) for k in ('artist', 'album_artist', 'album')},
    )
    parts = [_safe(p) for p in rel.replace('\\', '/').split('/') if p]
    if not parts:
        raise ValueError("template produced an empty path")
    # Append, don't with_suffix(): "01 Vol. 2" has no extension to replace.
    return str(Path(*parts)) + ext
