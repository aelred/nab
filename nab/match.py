""" Poorly-named module for formatting filenames. TODO: refactor and rename. """
import re
import unidecode
import difflib

_WORDSWAP = {
    "&": "and",
    "the": ""
}
_WORDSWAP_P = re.compile(r'( |^)(' + '|'.join(map(re.escape, _WORDSWAP)) +
                         r')( |$)', re.IGNORECASE)
_CHARSWAP = {
    "`": "'",
    "_": " ",
    "@": "",
    "~": "",
    ".": " ",
    ",": " ",
    "!": "",
    ":": "",
    "/": " ",
    "+": "",
    "'": ""
}
_CHARSWAP_P = re.compile('|'.join(map(re.escape, _CHARSWAP)), re.IGNORECASE)


def format_filename(fname):
    """ Format a filename, eliminating capitals and some punctuation. """
    formatted = fname
    if isinstance(formatted, unicode):
        formatted = unidecode.unidecode(fname)  # remove accented characters
    # perform any replacements from conversion dictionary
    formatted = _WORDSWAP_P.sub(
        lambda x: " " + _WORDSWAP[x.group(2).lower()] + " ",
        formatted)
    formatted = _CHARSWAP_P.sub(lambda x: _CHARSWAP[x.group().lower()],
                                formatted)
    formatted = re.sub(' +', ' ', formatted)  # squash repeated spaces
    formatted = formatted.lower().strip()  # title case and strip whitespace
    return formatted


def format_title(title):
    """ Format a title. Like format_filename, but removes hyphens. """
    formatted = re.sub(' -', '', title)  # remove hyphens from titles
    formatted = format_filename(formatted)
    return formatted


_JUNK = ":-[]@~., \t"


def comp(a, b, ignore=[]):
    """ Return the number of differences between two strings. """
    if isinstance(a, unicode):
        a = unidecode.unidecode(a)
    if isinstance(b, unicode):
        b = unidecode.unidecode(b)
    a = a.lower()
    b = b.lower()
    for ig in ignore:
        a = a.replace(ig.lower(), "")
        b = b.replace(ig.lower(), "")
    return difflib.SequenceMatcher(lambda c: c in _JUNK, a, b).ratio()


def closest_match(title, matches):
    """ Return the most similar string from a set of possible matches. """
    return max((comp(title, m), title) for m in matches)[1]
