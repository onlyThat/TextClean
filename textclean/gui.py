"""TextClean · 文本清洗小工具（图形界面）。

左边粘贴原文，勾选要做的清洗动作（或选一个预设），点「一键清洗」，
右边就是干净的结果，并提供「复制结果 / 保存为 txt」。

界面分区：
  顶部：预设下拉 + 选项勾选区
  中部：左「原文」 / 右「清洗结果」并排
  底部：一键清洗、复制、保存、字符统计
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import clean

APP_TITLE = "TextClean · 文本清洗小工具"

# 拖拽支持（可选）
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _HAS_DND = True
except Exception:  # pragma: no cover
    _HAS_DND = False

_FONT_UI = ("Microsoft YaHei UI", 10)
_FONT_MONO = ("Consolas", 10)


def _parse_drop(data: str) -> list[str]:
    paths: list[str] = []
    i, n = 0, len(data)
    while i < n:
        if data[i] == "{":
            j = data.find("}", i + 1)
            if j == -1:
                break
            paths.append(data[i + 1:j])
            i = j + 1
        elif data[i] == " ":
            i += 1
        else:
            j = i
            while j < n and data[j] != " ":
                j += 1
            paths.append(data[i:j])
            i = j
    return paths


class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("1180x760")
        root.minsize(900, 560)
        try:
            root.iconbitmap(default="")
        except Exception:
            pass

        self._build_top(root)
        self._build_editors(root)
        self._build_bottom(root)
        self._install_dnd()

    # ---------------- 顶部：预设 + 选项 ----------------
    def _build_top(self, root):
        top = ttk.Frame(root, padding=(10, 10, 10, 4))
        top.pack(fill="x")

        row1 = ttk.Frame(top)
        row1.pack(fill="x")
        ttk.Label(row1, text="预设：", font=_FONT_UI).pack(side="left")
        self.preset_var = tk.StringVar(value="默认（推荐）")
        self.preset_box = ttk.Combobox(
            row1, textvariable=self.preset_var, state="readonly", width=18,
            values=list(clean.PRESETS.keys()) + ["自定义"])
        self.preset_box.pack(side="left")
        self.preset_box.bind("<<ComboboxSelected>>", self._apply_preset)
        ttk.Label(row1, text="（选预设会自动勾好下面的选项，也可自己改）",
                  foreground="#888").pack(side="left", padx=8)

        opts = ttk.LabelFrame(top, text="清洗动作", padding=8)
        opts.pack(fill="x", pady=(8, 0))

        self.v_invisible = tk.BooleanVar(value=True)
        self.v_width = tk.BooleanVar(value=True)
        self.v_spaces = tk.BooleanVar(value=True)
        self.v_cjk_spaces = tk.BooleanVar(value=True)
        self.v_strip = tk.BooleanVar(value=True)
        self.v_blank = tk.BooleanVar(value=True)
        self.v_merge = tk.BooleanVar(value=False)
        self.v_outer = tk.BooleanVar(value=True)
        self.v_punct = tk.StringVar(value="none")

        grid = ttk.Frame(opts)
        grid.pack(fill="x")
        items = [
            ("去掉不可见字符（零宽空格 / 软连字符 / 控制符）", self.v_invisible),
            ("全角字母数字转半角、全角空格转普通空格", self.v_width),
            ("多个连续空格 / 制表符合并成一个", self.v_spaces),
            ("去掉汉字与汉字之间的空格", self.v_cjk_spaces),
            ("去掉每行首尾空白", self.v_strip),
            ("删除多余空行", self.v_blank),
            ("合并 PDF 折行（把断开的句子接起来）", self.v_merge),
            ("去掉整体首尾空行", self.v_outer),
        ]
        for i, (label, var) in enumerate(items):
            cb = ttk.Checkbutton(grid, text=label, variable=var,
                                 command=self._mark_custom)
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 24), pady=2)

        punct = ttk.Frame(opts)
        punct.pack(fill="x", pady=(6, 0))
        ttk.Label(punct, text="标点转换：", font=_FONT_UI).pack(side="left")
        for val, text in (("none", "不转换"), ("to_cn", "英文标点→中文"), ("to_en", "中文标点→英文")):
            ttk.Radiobutton(punct, text=text, value=val, variable=self.v_punct,
                            command=self._mark_custom).pack(side="left", padx=(0, 14))
        ttk.Label(punct, text="（中英混排时只转换句子内的标点，不动代码 / 数字）",
                  foreground="#888").pack(side="left")

    # ---------------- 中部：左右编辑区 ----------------
    def _build_editors(self, root):
        body = ttk.Frame(root, padding=(10, 4))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(body, text="原文（粘贴到这里，或拖入 .txt 文件）", padding=4)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.txt_in = self._make_text(left)

        right = ttk.LabelFrame(body, text="清洗结果（只读）", padding=4)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.txt_out = self._make_text(right, readonly=True)

    def _make_text(self, master, readonly=False):
        holder = ttk.Frame(master)
        holder.pack(fill="both", expand=True)
        txt = tk.Text(holder, wrap="word", undo=not readonly, font=_FONT_MONO,
                      relief="solid", bd=1, padx=8, pady=6,
                      bg="#fbfbfb" if not readonly else "#f4f7f4")
        vsb = ttk.Scrollbar(holder, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)
        txt.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        if readonly:
            txt.configure(state="disabled")
        else:
            txt.bind("<Control-Return>", lambda e: self.run_clean())
        return txt

    # ---------------- 底部：动作 ----------------
    def _build_bottom(self, root):
        bar = ttk.Frame(root, padding=(10, 4, 10, 10))
        bar.pack(fill="x")

        self.btn_clean = ttk.Button(bar, text="一键清洗  (Ctrl+Enter)", command=self.run_clean)
        self.btn_clean.pack(side="left")
        ttk.Button(bar, text="复制结果", command=self.copy_result).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="保存为 txt…", command=self.save_result).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="用结果替换原文", command=self.replace_input).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="清空", command=self.clear_all).pack(side="left", padx=(8, 0))

        self.stat_var = tk.StringVar(value="就绪")
        ttk.Label(bar, textvariable=self.stat_var, foreground="#666").pack(side="right")

    # ---------------- 行为 ----------------
    def _install_dnd(self):
        if not _HAS_DND:
            return
        for w in (self.txt_in,):
            try:
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

    def _on_drop(self, event):
        paths = _parse_drop(event.data)
        files = [p for p in paths if p.lower().endswith((".txt", ".md", ".csv", ".log"))]
        if not files:
            messagebox.showinfo("提示", "请拖入 .txt / .md / .csv / .log 文本文件。")
            return
        try:
            text = clean.read_text_file(files[0])
        except Exception as exc:
            messagebox.showerror("读取失败", str(exc))
            return
        self.txt_in.delete("1.0", "end")
        self.txt_in.insert("1.0", text)
        self.stat_var.set("已载入：%s" % files[0])

    def _apply_preset(self, _e=None):
        name = self.preset_var.get()
        opt = clean.PRESETS.get(name)
        if opt is None:
            return
        self.v_invisible.set(opt.remove_invisible)
        self.v_width.set(opt.normalize_width)
        self.v_spaces.set(opt.collapse_spaces)
        self.v_cjk_spaces.set(opt.remove_cjk_spaces)
        self.v_strip.set(opt.strip_lines)
        self.v_blank.set(opt.remove_blank_lines)
        self.v_merge.set(opt.merge_paragraphs)
        self.v_outer.set(opt.strip_outer)
        self.v_punct.set(opt.punct_mode)

    def _mark_custom(self):
        if self.preset_var.get() != "自定义":
            self.preset_var.set("自定义")

    def current_options(self) -> clean.CleanOptions:
        return clean.CleanOptions(
            remove_invisible=self.v_invisible.get(),
            normalize_width=self.v_width.get(),
            collapse_spaces=self.v_spaces.get(),
            remove_cjk_spaces=self.v_cjk_spaces.get(),
            strip_lines=self.v_strip.get(),
            remove_blank_lines=self.v_blank.get(),
            max_blank_lines=0,
            merge_paragraphs=self.v_merge.get(),
            strip_outer=self.v_outer.get(),
            punct_mode=self.v_punct.get(),
        )

    def run_clean(self):
        src = self.txt_in.get("1.0", "end-1c")
        if not src.strip():
            messagebox.showinfo("提示", "请先在左边粘贴或拖入要清洗的文本。")
            return
        result = clean.clean_text(src, self.current_options())
        self.txt_out.configure(state="normal")
        self.txt_out.delete("1.0", "end")
        self.txt_out.insert("1.0", result)
        self.txt_out.configure(state="disabled")
        st = clean.char_stats(src, result)
        self.stat_var.set(
            "字符 %d → %d（减少 %d），行数 %d → %d" % (
                st["before_chars"], st["after_chars"], st["saved_chars"],
                st["before_lines"], st["after_lines"]))

    def copy_result(self):
        text = self.txt_out.get("1.0", "end-1c")
        if not text:
            messagebox.showinfo("提示", "还没有清洗结果。")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.stat_var.set("已复制 %d 个字符到剪贴板" % len(text))

    def save_result(self):
        text = self.txt_out.get("1.0", "end-1c")
        if not text:
            messagebox.showinfo("提示", "还没有清洗结果。")
            return
        path = filedialog.asksaveasfilename(
            title="保存清洗结果", defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile="清洗结果.txt")
        if not path:
            return
        try:
            clean.write_text_file(path, text)
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))
            return
        self.stat_var.set("已保存：%s" % path)

    def replace_input(self):
        text = self.txt_out.get("1.0", "end-1c")
        if not text:
            return
        self.txt_in.delete("1.0", "end")
        self.txt_in.insert("1.0", text)
        self.stat_var.set("已用清洗结果替换原文")

    def clear_all(self):
        self.txt_in.delete("1.0", "end")
        self.txt_out.configure(state="normal")
        self.txt_out.delete("1.0", "end")
        self.txt_out.configure(state="disabled")
        self.stat_var.set("就绪")


def main():
    root = TkinterDnD.Tk() if _HAS_DND else tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()