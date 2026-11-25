"""TextClean · 文本清洗核心逻辑。

从 PDF / 网页 / 聊天记录里复制出来的文本常带着：多余空格、PDF 折行产生的
硬换行、零宽字符、全角字母数字、错乱的中英文标点。这里提供一套可勾选、
可组合的清洗步骤，纯函数、无界面依赖，方便测试。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# 字符集定义
# ---------------------------------------------------------------------------

# 汉字范围（基本区 + 扩展 A + 兼容区）
_CJK_CLS = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_CJK_RE = re.compile(f"[{_CJK_CLS}]")

# 零宽 / 方向控制 / 软连字符 / BOM 等不可见字符
_INVISIBLE_CHARS = (
    "\u200b\u200c\u200d\u200e\u200f"  # ZWSP ZWNJ ZWJ LRM RLM
    "\u2060\u2061\u2062\u2063\u2064"  # word joiner / invisible operators
    "\u180e\u061c"                    # mongolian vowel sep / arabic letter mark
    "\u00ad"                          # soft hyphen
    "\ufeff"                          # BOM / ZWNBSP
    "\ufff9\ufffa\ufffb"              # interlinear annotation
)

_INVISIBLE_TABLE = {ord(c): None for c in _INVISIBLE_CHARS}
# 不可打印控制字符（保留 \t \n \r，它们在上游已归一化 / 后续处理）
for _code in list(range(0x00, 0x09)) + [0x0B, 0x0C] + list(range(0x0E, 0x20)) + [0x7F]:
    _INVISIBLE_TABLE[_code] = None

# 全角字母 / 数字 → 半角
_WIDTH_TABLE = {}
for _i in range(10):
    _WIDTH_TABLE[ord("０") + _i] = ord("0") + _i
for _i in range(26):
    _WIDTH_TABLE[ord("Ａ") + _i] = ord("A") + _i
    _WIDTH_TABLE[ord("ａ") + _i] = ord("a") + _i

# 句末标点（用于判断是否应断段）
_TERMINAL_PUNCT = "。！？…；：.!?;:"
# 句末之后可能紧跟的收尾符号
_CLOSERS = "”’\"'）)】》」』〉"

# 列表 / 小标题起始标记 —— 遇到时不应与上一行合并
_LIST_START_RE = re.compile(
    r"^(?:"
    r"\d+[.、)）]"                    # 1.  1、  1)
    r"|[一二三四五六七八九十百千]+[、.．]"  # 一、  二.
    r"|[（(]\d+[)）]"                  # (1)  （1）
    r"|[•·▪◦‣∙*\-–—]"                 # 项目符号
    r"|第[一二三四五六七八九十百千\d]+[章节条款部分]"  # 第 1 章
    r")"
)

# 中文 → 英文标点
_TO_EN_TABLE = {
    "，": ",", "。": ".", "！": "!", "？": "?", "；": ";", "：": ":",
    "（": "(", "）": ")", "【": "[", "】": "]", "《": "<", "》": ">",
    "「": '"', "」": '"', "『": '"', "』": '"', "、": ",",
    "“": '"', "”": '"', "‘": "'", "’": "'", "·": ".",
}


# ---------------------------------------------------------------------------
# 选项
# ---------------------------------------------------------------------------

@dataclass
class CleanOptions:
    """一次清洗的可选项。默认值即「推荐」配置。"""

    remove_invisible: bool = True      # 去掉零宽字符、控制字符、软连字符等
    normalize_width: bool = True       # 全角空格→空格、全角字母数字→半角
    collapse_spaces: bool = True       # 多个连续空格/制表符合并成一个
    remove_cjk_spaces: bool = True     # 去掉汉字与汉字之间的空格
    strip_lines: bool = True           # 去掉每行首尾空白
    remove_blank_lines: bool = True    # 删除多余空行
    max_blank_lines: int = 0           # 最多保留几个连续空行（0 = 全删）
    merge_paragraphs: bool = False     # 合并 PDF 折行产生的硬换行
    strip_outer: bool = True           # 去掉首尾整体空行
    punct_mode: str = "none"           # none / to_cn / to_en


# 常用预设
PRESETS: dict[str, CleanOptions] = {
    "默认（推荐）": CleanOptions(),
    "PDF 复制文本": CleanOptions(
        merge_paragraphs=True, remove_cjk_spaces=True,
    ),
    "网页 / 聊天记录": CleanOptions(
        merge_paragraphs=False, max_blank_lines=1,
    ),
    "只去乱码空格": CleanOptions(
        collapse_spaces=True, remove_cjk_spaces=True,
        strip_lines=True, remove_blank_lines=False,
    ),
    "转中文标点": CleanOptions(punct_mode="to_cn"),
    "转英文标点": CleanOptions(punct_mode="to_en"),
}


# ---------------------------------------------------------------------------
# 步骤实现
# ---------------------------------------------------------------------------

def _strip_invisible(text: str) -> str:
    # 垂直制表 / 换页当作换行
    text = text.replace("\x0b", "\n").replace("\x0c", "\n")
    # 行分隔符 / 段分隔符
    text = text.replace("\u2028", "\n").replace("\u2029", "\n")
    return text.translate(_INVISIBLE_TABLE)


def _normalize_width(text: str) -> str:
    text = text.translate(_WIDTH_TABLE)
    return text.replace("\u3000", " ")


def _collapse_line(line: str, remove_cjk_spaces: bool) -> str:
    line = re.sub(r"[ \t]+", " ", line)
    if remove_cjk_spaces:
        # 汉字 汉字 之间的空格
        line = re.sub(
            f"(?<=[{_CJK_CLS}]) +(?=[{_CJK_CLS}])", "", line
        )
        # 汉字 与 中文标点 之间的空格
        line = re.sub(
            f"(?<=[{_CJK_CLS}]) +(?=[，。！？；：、）】》”’])", "", line
        )
        line = re.sub(
            f"(?<=[（【《“‘]) +(?=[{_CJK_CLS}])", "", line
        )
    return line


def _line_ends_sentence(line: str) -> bool:
    t = line.rstrip()
    while t and t[-1] in _CLOSERS:
        t = t[:-1]
    return bool(t) and t[-1] in _TERMINAL_PUNCT


def _join_lines(left: str, right: str) -> str:
    # 英文连字符断行： inter- \n national → international
    if (left.endswith("-") and len(left) >= 2
            and left[-2].isalpha() and right[:1].islower()):
        return left[:-1] + right
    # 汉字接汉字：直接相连
    if _CJK_RE.match(left[-1]) and _CJK_RE.match(right[0]):
        return left + right
    return left + " " + right


def _merge_paragraphs(text: str) -> str:
    out: list[str] = []
    buf: str | None = None
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            if buf is not None:
                out.append(buf)
                buf = None
            out.append("")
            continue
        if buf is None:
            buf = line
            continue
        if _line_ends_sentence(buf) or _LIST_START_RE.match(line):
            out.append(buf)
            buf = line
        else:
            buf = _join_lines(buf, line)
    if buf is not None:
        out.append(buf)
    return "\n".join(out)


def _collapse_blank_lines(text: str, max_keep: int) -> str:
    max_keep = max(0, int(max_keep))
    out: list[str] = []
    blanks = 0
    for line in text.split("\n"):
        if line.strip() == "":
            blanks += 1
            if blanks <= max_keep:
                out.append("")
        else:
            blanks = 0
            out.append(line)
    return "\n".join(out)


def _convert_double_quotes_to_cn(text: str) -> str:
    res: list[str] = []
    opening = True
    for ch in text:
        if ch == '"':
            res.append("“" if opening else "”")
            opening = not opening
        else:
            if ch == "\n":
                opening = True
            res.append(ch)
    return "".join(res)


def _to_cn_punct(text: str) -> str:
    out: list[str] = []
    n = len(text)
    for i, ch in enumerate(text):
        prev = text[i - 1] if i > 0 else ""
        nxt = text[i + 1] if i + 1 < n else ""
        prev_cjk = bool(_CJK_RE.match(prev)) if prev else False
        next_cjk = bool(_CJK_RE.match(nxt)) if nxt else False
        if ch == "," and (prev_cjk or next_cjk):
            out.append("，")
        elif ch == "." and prev_cjk and (nxt == "" or nxt not in "0123456789"):
            out.append("。")
        elif ch == "!" and (prev_cjk or next_cjk):
            out.append("！")
        elif ch == "?" and (prev_cjk or next_cjk):
            out.append("？")
        elif ch == ";" and (prev_cjk or next_cjk):
            out.append("；")
        elif ch == ":" and (prev_cjk or next_cjk):
            out.append("：")
        elif ch == "(" and (next_cjk or (i + 2 < n and _CJK_RE.match(text[i + 2]))):
            out.append("（")
        elif ch == ")" and prev_cjk:
            out.append("）")
        else:
            out.append(ch)
    text = "".join(out)
    text = _convert_double_quotes_to_cn(text)
    text = re.sub(r"\.{3,}", "……", text)
    return text


def _to_en_punct(text: str) -> str:
    text = re.sub(r"…+", "...", text)
    text = text.replace("——", "--").replace("—", "-")
    text = "".join(_TO_EN_TABLE.get(ch, ch) for ch in text)
    # 英文标点后面紧跟英文/数字时补一个空格（hello，world → hello, world）
    text = re.sub(r"([,;:])(?=[A-Za-z0-9])", r"\1 ", text)
    text = re.sub(r"(?<=[A-Za-z0-9])([.!?])(?=[A-Za-z])", r"\1 ", text)
    return text


# ---------------------------------------------------------------------------
# 对外主函数
# ---------------------------------------------------------------------------

def clean_text(text: str, options: CleanOptions | None = None) -> str:
    """按选项清洗文本，返回清洗结果。输入为空时返回空串。"""
    if not text:
        return ""
    opt = options or CleanOptions()

    s = text.replace("\r\n", "\n").replace("\r", "\n")

    if opt.remove_invisible:
        s = _strip_invisible(s)
    if opt.normalize_width:
        s = _normalize_width(s)
    if opt.punct_mode == "to_cn":
        s = _to_cn_punct(s)
    elif opt.punct_mode == "to_en":
        s = _to_en_punct(s)

    lines = s.split("\n")
    if opt.strip_lines:
        lines = [ln.strip(" \t") for ln in lines]
    if opt.collapse_spaces:
        lines = [_collapse_line(ln, opt.remove_cjk_spaces) for ln in lines]
    s = "\n".join(lines)

    if opt.merge_paragraphs:
        s = _merge_paragraphs(s)
    if opt.remove_blank_lines:
        s = _collapse_blank_lines(s, opt.max_blank_lines)
    if opt.strip_outer:
        s = s.strip("\n")
    return s


def char_stats(before: str, after: str) -> dict[str, int]:
    """统计清洗前后的字符数、行数对比。"""
    def _lines(t: str) -> int:
        return 0 if not t else t.count("\n") + 1
    return {
        "before_chars": len(before),
        "after_chars": len(after),
        "saved_chars": len(before) - len(after),
        "before_lines": _lines(before),
        "after_lines": _lines(after),
    }


_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "utf-16", "latin-1")


def read_text_file(path: str) -> str:
    """按常见编码依次尝试读取文本文件。"""
    with open(path, "rb") as f:
        raw = f.read()
    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def write_text_file(path: str, text: str, encoding: str = "utf-8") -> None:
    with open(path, "w", encoding=encoding, newline="\n") as f:
        f.write(text)