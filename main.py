"""TextClean 启动入口。

双击 exe 或运行 `python main.py` 打开界面。任何未捕获异常会写入
同目录的 textclean-error.log，并把提示弹出来，避免 windowed 模式下
「窗口一闪而过」。
"""
import os
import sys
import traceback


def _log_path():
    base = os.path.dirname(os.path.abspath(
        sys.executable if getattr(sys, "frozen", False) else __file__))
    p = os.path.join(base, "textclean-error.log")
    try:
        with open(p, "a", encoding="utf-8"):
            pass
        return p
    except OSError:
        return os.path.join(os.path.expanduser("~"), "textclean-error.log")


def _install_crash_logger():
    def hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            with open(_log_path(), "a", encoding="utf-8") as f:
                f.write(text + "\n" + "-" * 60 + "\n")
        except Exception:
            pass
        try:
            import tkinter as tk
            import tkinter.messagebox as mb
            r = tk.Tk()
            r.withdraw()
            mb.showerror("TextClean 启动失败",
                         "程序遇到错误：\n%s\n\n详细信息已写入：\n%s" % (exc, _log_path()))
            r.destroy()
        except Exception:
            pass

    sys.excepthook = hook


if getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.dirname(sys.executable))
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    _install_crash_logger()
    try:
        from textclean.gui import main
        main()
    except Exception:
        sys.excepthook(*sys.exc_info())