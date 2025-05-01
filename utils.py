import re
from typing import List


def clean_response(text: str) -> str:

    text = re.sub(r'\$\$(.*?)\$\$', r'\1', text)
    text = re.sub(r'\$(.*?)\$', r'\1', text)

    text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)

    text = re.sub(r'\s+', ' ', text).strip()

    return text


def escape_markdown(text: str) -> str:
    """
    Экранирует MarkdownV2-символы, обрабатывает **жирный**, `code`, > цитаты и списки.
    Также заменяет:
    - x^2 → x², x^(n+1) → x⁽ⁿ⁺¹⁾
    - x_2 → x₂, x_(n+1) → xₙ₊₁
    - sqrt(x) → √x
    - 1/2 → ½ и др.
    """

    text = replace_math_symbols(text)

    code_blocks = re.findall(r'```(.*?)```', text, flags=re.DOTALL)
    for i, block in enumerate(code_blocks):
        placeholder = f"<<CODE_BLOCK_{i}>>"
        text = text.replace(f"```{block}```", placeholder)

    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)

    escape_chars = r"_*[]()~`>#+-=|{}.!"
    text = re.sub(f"([{re.escape(escape_chars)}])", r'\\\1', text)

    text = re.sub(r'^(\d+)\.', r'\1\\.', text, flags=re.MULTILINE)

    for i, block in enumerate(code_blocks):
        placeholder = f"<<CODE_BLOCK_{i}>>"
        clean_block = block.replace('\\', '\\\\')
        safe_code = f"```{clean_block}```"
        text = text.replace(placeholder, safe_code)

    return text


def replace_math_symbols(text: str) -> str:
    text = replace_powers(text)
    text = replace_subscripts(text)
    text = replace_square_roots(text)
    text = replace_fractions(text)
    return text


def replace_powers(text: str) -> str:
    superscript_map = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³',
        '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷',
        '8': '⁸', '9': '⁹', '+': '⁺', '-': '⁻',
        '=': '⁼', '(': '⁽', ')': '⁾',
        'n': 'ⁿ', 'i': 'ⁱ', 'x': 'ˣ', 'y': 'ʸ', 'a': 'ᵃ',
        'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ', 'f': 'ᶠ',
        'g': 'ᵍ', 'h': 'ʰ', 'j': 'ʲ', 'k': 'ᵏ', 'l': 'ˡ',
        'm': 'ᵐ', 'o': 'ᵒ', 'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ',
        't': 'ᵗ', 'u': 'ᵘ', 'v': 'ᵛ', 'w': 'ʷ', 'z': 'ᶻ',
    }

    def to_superscript(s: str) -> str:
        return ''.join(superscript_map.get(char, char) for char in s)

    text = re.sub(r'(\w)\^\(([^)]+)\)', lambda m: m.group(1) + to_superscript('(' + m.group(2) + ')'), text)
    text = re.sub(r'(\w)\^([a-zA-Z0-9\+\-\=]+)', lambda m: m.group(1) + to_superscript(m.group(2)), text)
    return text


def replace_subscripts(text: str) -> str:
    subscript_map = {
        '0': '₀', '1': '₁', '2': '₂', '3': '₃',
        '4': '₄', '5': '₅', '6': '₆', '7': '₇',
        '8': '₈', '9': '₉', '+': '₊', '-': '₋',
        '=': '₌', '(': '₍', ')': '₎',
        'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',
        'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ',
        'o': 'ₒ', 'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ',
        't': 'ₜ', 'u': 'ᵤ', 'v': 'ᵥ', 'x': 'ₓ'
    }

    def to_subscript(s: str) -> str:
        return ''.join(subscript_map.get(char, char) for char in s)

    text = re.sub(r'(\w)_\(([^)]+)\)', lambda m: m.group(1) + to_subscript(m.group(2)), text)
    text = re.sub(r'(\w)_([a-zA-Z0-9\+\-\=]+)', lambda m: m.group(1) + to_subscript(m.group(2)), text)
    return text


def replace_square_roots(text: str) -> str:
    return re.sub(r'sqrt\(([^)]+)\)', r'√\1', text)


def replace_fractions(text: str) -> str:
    fraction_map = {
        '1/2': '½', '1/3': '⅓', '2/3': '⅔',
        '1/4': '¼', '3/4': '¾',
        '1/5': '⅕', '2/5': '⅖', '3/5': '⅗', '4/5': '⅘',
        '1/6': '⅙', '5/6': '⅚',
        '1/7': '⅐', '1/8': '⅛', '3/8': '⅜', '5/8': '⅝', '7/8': '⅞',
        '1/9': '⅑', '1/10': '⅒',
    }

    for frac, symbol in fraction_map.items():
        text = text.replace(frac, symbol)
    return text


def split_text(text: str, max_len: int = 4096) -> List[str]:
    parts = []
    while len(text) > max_len:
        split_pos = text.rfind(' ', 0, max_len)
        if split_pos == -1:
            split_pos = max_len
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()
    parts.append(text)
    return parts
