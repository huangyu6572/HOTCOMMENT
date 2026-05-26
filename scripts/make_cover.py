"""
封面图生成工具 — 输出到 data/ 目录

用法:
  python scripts/make_cover.py --title "最后的净土还是最后的收费站？" --subtitle "稻城亚丁截断40公里省道收费" --output cover_daocheng
"""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def make_cover(title: str, subtitle: str = "", output: str = "cover") -> str:
    """生成 1080x1440 深色风格封面，返回保存路径"""
    img = Image.new("RGB", (1080, 1440), color=(24, 28, 36))
    d = ImageDraw.Draw(img)

    try:
        f_large = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 64)
        f_medium = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 36)
        f_small = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 28)
    except Exception:
        f_large = f_medium = f_small = ImageFont.load_default()

    # 主标题（支持换行）
    lines = title.split("\\n")
    y = 250
    for line in lines:
        if y < 450:
            fill = (255, 200, 60) if y == 250 else (255, 90, 70)
            d.text((80, y), line.strip(), fill=fill, font=f_large)
            y += 100
        else:
            d.text((80, y), line.strip(), fill=(200, 200, 210), font=f_medium)
            y += 60

    # 副标题
    if subtitle:
        d.text((80, 550), subtitle, fill=(180, 180, 190), font=f_medium)

    # 底部引导
    d.text((80, 1250), "评论区聊聊你的看法", fill=(255, 200, 60), font=f_medium)

    path = str(DATA_DIR / f"{output}.jpg")
    img.save(path, "JPEG", quality=95)
    return path


def main():
    parser = argparse.ArgumentParser(description="生成小红书封面图")
    parser.add_argument("--title", required=True, help="主标题（\\n 换行）")
    parser.add_argument("--subtitle", default="", help="副标题")
    parser.add_argument("--output", default="cover", help="输出文件名（不含扩展名）")
    args = parser.parse_args()

    path = make_cover(args.title, args.subtitle, args.output)
    print(f"✅ 封面已生成: {path}")


if __name__ == "__main__":
    main()
