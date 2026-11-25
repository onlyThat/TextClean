"""TextClean 核心清洗逻辑测试。运行：python tests/test_core.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from textclean import clean  # noqa: E402
from textclean.clean import CleanOptions  # noqa: E402

PASS = 0
FAIL = 0


def check(name, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
        print("  [OK] %s" % name)
    else:
        FAIL += 1
        print("  [FAIL] %s\n     got : %r\n     want: %r" % (name, got, want))


# ---------------------------------------------------------------- 不可见字符
print("== 不可见字符 ==")
check("零宽空格被删除",
      clean.clean_text("你\u200b好\u200d世界"),
      "你好世界")
check("软连字符被删除",
      clean.clean_text("abc\u00addef"),
      "abcdef")
check("BOM 被删除",
      clean.clean_text("\ufeff标题"),
      "标题")
check("控制字符被删除",
      clean.clean_text("a\x00b\x07c"),
      "abc")
check("LRM/RLM 被删除",
      clean.clean_text("a\u200eb\u200fc"),
      "abc")

# ---------------------------------------------------------------- 宽度归一
print("== 宽度归一 ==")
check("全角空格转普通空格再合并",
      clean.clean_text("甲\u3000乙", CleanOptions(remove_cjk_spaces=False)),
      "甲 乙")
check("全角数字转半角",
      clean.clean_text("１２３４", CleanOptions()),
      "1234")
check("全角字母转半角",
      clean.clean_text("ＡＢＣｘｙｚ", CleanOptions()),
      "ABCxyz")

# ---------------------------------------------------------------- 空格处理
print("== 空格处理 ==")
check("多空格合并",
      clean.clean_text("a     b\t\tc"),
      "a b c")
check("汉字间空格被删",
      clean.clean_text("今 天 天 气 很 好"),
      "今天天气很好")
check("中英之间空格保留",
      clean.clean_text("使用 Python 编写"),
      "使用 Python 编写")
check("汉字与中文标点间空格被删",
      clean.clean_text("你好 ，世界 。"),
      "你好，世界。")
check("行首行尾空白被删",
      clean.clean_text("  开头\n结尾  "),
      "开头\n结尾")

# ---------------------------------------------------------------- 空行
print("== 空行 ==")
check("多余空行被删除",
      clean.clean_text("第一段\n\n\n\n第二段"),
      "第一段\n第二段")
check("保留一个空行",
      clean.clean_text("第一段\n\n\n\n第二段",
                       CleanOptions(max_blank_lines=1)),
      "第一段\n\n第二段")
check("首尾空行被去掉",
      clean.clean_text("\n\n正文\n\n"),
      "正文")

# ---------------------------------------------------------------- 段落合并
print("== 段落合并 ==")
check("中文折行被接上",
      clean.clean_text("这是一段被 PDF\n折行的中文文本。",
                       CleanOptions(merge_paragraphs=True)),
      "这是一段被 PDF 折行的中文文本。")
check("句末不合并",
      clean.clean_text("第一句。\n第二句。",
                       CleanOptions(merge_paragraphs=True)),
      "第一句。\n第二句。")
check("列表项不合并",
      clean.clean_text("标题\n1. 第一项",
                       CleanOptions(merge_paragraphs=True)),
      "标题\n1. 第一项")
check("中文列表项不合并",
      clean.clean_text("正文\n一、总则",
                       CleanOptions(merge_paragraphs=True)),
      "正文\n一、总则")
check("英文连字符断词被拼接",
      clean.clean_text("inter-\nnational",
                       CleanOptions(merge_paragraphs=True)),
      "international")
check("英文折行用空格连接",
      clean.clean_text("hello\nworld",
                       CleanOptions(merge_paragraphs=True)),
      "hello world")
check("空行分段落仍分开",
      clean.clean_text("段落一的内容\n仍在继续\n\n段落二",
                       CleanOptions(merge_paragraphs=True)),
      "段落一的内容仍在继续\n段落二")

# ---------------------------------------------------------------- 标点转换
print("== 标点转换 ==")
opt_cn = CleanOptions(punct_mode="to_cn", remove_cjk_spaces=False)
check("英文逗号转中文",
      clean.clean_text("你好,世界", opt_cn),
      "你好，世界")
check("英文句号转中文",
      clean.clean_text("结束了.", opt_cn),
      "结束了。")
check("小数点不动",
      clean.clean_text("圆周率是 3.14 左右", opt_cn),
      "圆周率是 3.14 左右")
check("英文问号感叹号转中文",
      clean.clean_text("真的吗?是的!", opt_cn),
      "真的吗？是的！")
check("英文括号转中文",
      clean.clean_text("示例(说明)", opt_cn),
      "示例（说明）")
check("双引号转中文引号",
      clean.clean_text('他说"你好"。', opt_cn),
      "他说“你好”。")

opt_en = CleanOptions(punct_mode="to_en")
check("中文逗号转英文",
      clean.clean_text("hello，world", opt_en),
      "hello, world")
check("中文句号转英文",
      clean.clean_text("结束。", opt_en),
      "结束.")
check("中文省略号转三点",
      clean.clean_text("等等……", opt_en),
      "等等...")

# ---------------------------------------------------------------- 组合 / 预设
print("== 组合与预设 ==")
pdf_noise = (
    "　　　　第一章  总  则\n\n\n"
    "第一条  为 了 规 范\u200b 管 理 ，\n"
    "制 定 本 办 法 。\n\n\n\n"
    "第二条  本办法\n适用于全体员工。\n"
)
res = clean.clean_text(pdf_noise, clean.PRESETS["PDF 复制文本"])
check("PDF 预设：无零宽字符", "\u200b" in res, False)
check("PDF 预设：无全角空格", "\u3000" in res, False)
check("PDF 预设：无三连空行", "\n\n\n" in res, False)
check("PDF 预设：汉字空格已清理", "为 了" in res, False)
check("PDF 预设：断句已合并", "本办法适用于全体员工。" in res, True)

check("空输入返回空串", clean.clean_text(""), "")
check("预设数量", len(clean.PRESETS) >= 5, True)

# ---------------------------------------------------------------- 统计
print("== 统计与文件 IO ==")
st = clean.char_stats("一二三\n四", "一二三")
check("字符统计 before", st["before_chars"], 5)
check("字符统计 after", st["after_chars"], 3)
check("行数统计", st["before_lines"], 2)

here = os.path.dirname(os.path.abspath(__file__))
tmp = os.path.join(here, "_tmp_io.txt")
clean.write_text_file(tmp, "测试内容\n第二行", encoding="utf-8")
back = clean.read_text_file(tmp)
check("写读往返一致", back, "测试内容\n第二行")
os.remove(tmp)

# GBK 文件读取
tmp_gbk = os.path.join(here, "_tmp_gbk.txt")
with open(tmp_gbk, "wb") as f:
    f.write("中文GBK编码".encode("gb18030"))
check("GBK 文件自动识别", clean.read_text_file(tmp_gbk), "中文GBK编码")
os.remove(tmp_gbk)

print("\n结果：%d 通过，%d 失败" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)