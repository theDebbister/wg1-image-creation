from __future__ import annotations


def reorder_ltr_runs(words: list) -> list:
    """Prepare LTR (Latin) word runs in a Hebrew paragraph for char-by-char RTL rendering.

    Hebrew text is drawn character-by-character right-to-left. For Latin characters
    drawn in RTL order to appear visually correct (left-to-right), each Latin word's
    characters must be reversed before rendering. Multi-word Latin runs also need their
    word order reversed, so the entire phrase reads correctly after RTL placement.
    """
    def is_ltr_word(w):
        # treat word as LTR if it has ASCII letters or digits but no Hebrew characters
        has_hebrew = any('֐' <= c <= '׿' for c in w)
        has_ascii = any(ord(c) < 128 and (c.isalpha() or c.isdigit()) for c in w)
        return has_ascii and not has_hebrew

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
        else:
            i += 1
    return words