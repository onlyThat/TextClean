"""生成 textclean.ico：一支扫帚扫走杂点的简洁图标。

青色圆角背景 + 白色文本行 + 一把扫帚，寓意「把乱码扫干净」。
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "textclean.ico")


def draw(size: int) -> Image.Image:
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = int(s * 0.08)
    d.rounded_rectangle([pad, pad, s - pad, s - pad], radius=int(s * 0.20),
                        fill=(16, 148, 138, 255))

    # 三行文本条（白色带点灰，暗示原文），越往下越短
    line_x0 = int(s * 0.16)
    widths = [0.42, 0.34, 0.24]
    for i, w in enumerate(widths):
        y = int(s * 0.26) + i * int(s * 0.13)
        d.rounded_rectangle([line_x0, y, line_x0 + int(s * w), y + int(s * 0.07)],
                            radius=int(s * 0.035),
                            fill=(255, 255, 255, 255) if i != 1 else (200, 235, 232, 255))

    # 扫帚：斜柄 + 扫毛
    handle_col = (255, 214, 102, 255)
    bx0, by0 = int(s * 0.62), int(s * 0.22)
    bx1, by1 = int(s * 0.78), int(s * 0.58)
    d.line([bx0, by0, bx1, by1], fill=handle_col, width=max(2, int(s * 0.06)))
    # 扫毛（扇形）
    for k in range(-2, 3):
        hx = bx1 + k * int(s * 0.055)
        d.line([bx1, by1, hx, by1 + int(s * 0.16)],
               fill=(245, 245, 245, 255), width=max(1, int(s * 0.028)))
    return img


def main():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [draw(sz) for sz in sizes]
    imgs[-1].save(OUT, format="ICO", sizes=[(sz, sz) for sz in sizes])
    print("icon written:", OUT)


if __name__ == "__main__":
    main()