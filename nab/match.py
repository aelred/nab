import re
import unidecode
import difflib

wordswap = {
    "&": "and",
    "the": ""
}
wordswap_p = re.compile(r'( |^)(' + '|'.join(map(re.escape, wordswap)) +
                        r')( |$)',
                        re.IGNORECASE)
charswap = {
    "`": "'",
    "_": " ",
    "@": "",
    "~": "",
    ".": " ",
    ",": " ",
    "!": "",
    ":": "",
    "/": " ",
    "+": ""
}
charswap_p = re.compile('|'.join(map(re.escape, charswap)),
                        re.IGNORECASE)


def format_filename(fname):
    formatted = fname
    if isinstance(formatted, unicode):
        formatted = unidecode.unidecode(fname)  # remove accented characters
    # perform any replacements from conversion dictionary
    formatted = wordswap_p.sub(
        lambda x: " " + wordswap[x.group(2).lower()] + " ",
        formatted)
    formatted = charswap_p.sub(lambda x: charswap[x.group().lower()],
                               formatted)
    formatted = re.sub(' +', ' ', formatted)  # squash repeated spaces
    formatted = formatted.lower().strip()  # title case and strip whitespace
    return formatted


def format_title(title):
    formatted = re.sub(' -', '', title)  # remove hyphens from titles
    formatted = format_filename(formatted)
    return formatted


junk = ":-[]@~., \t"


def comp(a, b, ignore=[]):
    if isinstance(a, unicode):
        a = unidecode.unidecode(a)
    if isinstance(b, unicode):
        b = unidecode.unidecode(b)
    a = a.lower()
    b = b.lower()
    for ig in ignore:
        a = a.replace(ig.lower(), "")
        b = b.replace(ig.lower(), "")
    return difflib.SequenceMatcher(lambda c: c in junk, a, b).ratio()


def closest_match(title, matches):
    return max((comp(title, m), title) for m in matches)[1]
