"""GUI 无头测试：隐藏窗口构造界面，喂文本、点清洗、验证结果与统计。
运行：python tests/test_gui_headless.py
"""
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from textclean import gui  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [OK] %s" % name)
    else:
        FAIL += 1
        print("  [FAIL] %s %s" % (name, detail))


root = tk.Tk()
root.withdraw()  # 不真的显示窗口
app = gui.App(root)
root.update_idletasks()

print("== 界面构造 ==")
check("窗口标题", root.title() == gui.APP_TITLE, root.title())
check("预设下拉有内容", len(app.preset_box["values"]) >= 5)
check("左右编辑区存在", app.txt_in.winfo_exists() and app.txt_out.winfo_exists())

print("== 预设切换 ==")
app.preset_var.set("PDF 复制文本")
app._apply_preset()
check("PDF 预设勾选合并", app.v_merge.get() is True)
check("PDF 预设未选标点转换", app.v_punct.get() == "none")

print("== 一键清洗 ==")
noisy = "　　　标题\u200b\n\n\n\n正文  有  多余空格 。"
# 结果区是 disabled，插入要先临时允许写 —— 模拟用户粘贴
app.txt_in.delete("1.0", "end")
app.txt_in.insert("1.0", noisy)
app.run_clean()
out = app.txt_out.get("1.0", "end-1c")
check("零宽字符已清掉", "\u200b" not in out, repr(out))
check("空行已压缩", "\n\n\n" not in out, repr(out))
check("统计已更新", "→" in app.stat_var.get(), app.stat_var.get())

print("== 用结果替换原文 ==")
app.replace_input()
check("原文被替换", app.txt_in.get("1.0", "end-1c") == out)

print("== 清空 ==")
app.clear_all()
check("原文清空", app.txt_in.get("1.0", "end-1c") == "")
check("结果清空", app.txt_out.get("1.0", "end-1c") == "")

root.destroy()
print("\n结果：%d 通过，%d 失败" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)