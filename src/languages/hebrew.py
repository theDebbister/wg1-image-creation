from __future__ import annotations
import unicodedata


def split_grapheme_clusters(text: str) -> list[str]:
    """Split Hebrew text into grapheme clusters (base character + following combining marks).

    Hebrew niqqud (vowel points) and cantillation marks are Unicode combining characters.
    Drawing them as isolated code points causes fonts to insert a dotted-circle placeholder.
    This function groups each base character with its following combining marks so the whole
    grapheme is passed to draw.text() as a single unit.
    """
    clusters = []
    current = ''
    for char in text:
        if unicodedata.combining(char):
            current += char
        else:
            if current:
                clusters.append(current)
            current = char
    if current:
        clusters.append(current)
    return clusters


def _reverse_latin_runs_in_mixed_word(word: str) -> str:
    """Reverse each Latin/numeric run within a Hebrew+Latin mixed word.

    In char-by-char RTL rendering, a Latin substring like 'DNA' would appear backwards
    ('AND') unless its characters are pre-reversed. This function handles words that
    contain both Hebrew and Latin/numeric characters (e.g. 'ה-DNA', 'ב-23', 'ה-34-18').

    A 'Latin run' is a maximal sequence of ASCII alphanumeric characters, allowing
    ASCII punctuation (e.g. hyphen, comma) to be included when they appear between
    two alphanumeric characters — so '34-18' and '15,000' each reverse as one unit.
    Trailing punctuation (e.g. the comma in '1722,') is excluded from the run.
    """
    chars = list(word)
    i = 0
    while i < len(chars):
        if ord(chars[i]) < 128 and chars[i].isalnum():
            j = i + 1
            while j < len(chars):
                c = chars[j]
                if ord(c) < 128 and c.isalnum():
                    j += 1
                elif (ord(c) < 128 and not c.isspace()
                        and j + 1 < len(chars)
                        and ord(chars[j + 1]) < 128 and chars[j + 1].isalnum()):
                    # ASCII connector (hyphen, comma, …) between two alphanumeric chars:
                    # include it in the run so '34-18' and '15,000' reverse as units.
                    j += 1
                else:
                    break
            chars[i:j] = chars[i:j][::-1]
            i = j
        else:
            i += 1
    return ''.join(chars)


def reorder_ltr_runs(words: list) -> list:
    """Prepare LTR (Latin) word runs in a Hebrew paragraph for char-by-char RTL rendering.

    Hebrew text is drawn character-by-character right-to-left. For Latin characters
    drawn in RTL order to appear visually correct (left-to-right), each Latin word's
    characters must be reversed before rendering. Multi-word Latin runs also need their
    word order reversed, so the entire phrase reads correctly after RTL placement.

    For words that mix Hebrew and Latin characters (e.g. 'ה-DNA', 'ב-23', 'ש-MultiplEYE'),
    the Latin/numeric runs within the word are reversed in place.
    """
    def is_ltr_word(w):
        # treat word as LTR if it has ASCII letters or digits but no Hebrew characters
        has_hebrew = any('֐' <= c <= '׿' for c in w)
        has_ascii = any(ord(c) < 128 and c.isalnum() for c in w)
        return has_ascii and not has_hebrew

    def is_mixed_word(w):
        has_hebrew = any('֐' <= c <= '׿' for c in w)
        has_ascii = any(ord(c) < 128 and c.isalnum() for c in w)
        return has_hebrew and has_ascii

    i = 0
    while i < len(words):
        if is_ltr_word(words[i]):
            j = i + 1
            while j < len(words) and is_ltr_word(words[j]):
                j += 1
            for k in range(i, j):
                words[k] = words[k][::-1]
            if j - i > 1:
                words[i:j] = words[i:j][::-1]
            i = j
        elif is_mixed_word(words[i]):
            words[i] = _reverse_latin_runs_in_mixed_word(words[i])
            i += 1
        else:
            i += 1
    return words