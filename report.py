"""
每周简报 PNG 生成器
输入：数据库中的 is_new=1 皮肤（本次新增）
输出：reports/weekly_YYYY-MM-DD.png
用途：每周跑完爬虫后自动生成一张可分享的图，直观展示本周新皮肤
"""
import io
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

import db

REPORT_DIR = Path(__file__).parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)

# 视觉参数
WIDTH = 1200
BG_COLOR = (15, 23, 42)          # slate-900
CARD_BG = (30, 41, 59)           # slate-800
ACCENT = (251, 146, 60)          # orange-400
TEXT_LIGHT = (226, 232, 240)     # slate-200
TEXT_MUTED = (148, 163, 184)     # slate-400
THUMB_SIZE = 180
THUMB_PER_ROW = 5
THUMB_GAP = 16
CARD_HEIGHT = THUMB_SIZE + 60    # 缩略图 + 名字区
MAX_ITEMS_PER_GAME = 10          # 每游戏最多展示前 N 张


def _load_font(size: int, bold: bool = False):
    """Windows 内置字体优先中文"""
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _download_thumb(url: str) -> Image.Image | None:
    """下载图片并缩放到 THUMB_SIZE 方形（不足留黑边）"""
    try:
        r = requests.get(url, timeout=15,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
    except Exception:
        return None

    img.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
    # 居中放到方形画布
    canvas = Image.new("RGBA", (THUMB_SIZE, THUMB_SIZE), (15, 23, 42, 255))
    x = (THUMB_SIZE - img.width) // 2
    y = (THUMB_SIZE - img.height) // 2
    canvas.paste(img, (x, y), img)
    return canvas


def _text_wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    """单行截断（超过就 ...）"""
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + "...", font=font) > max_width:
        text = text[:-1]
    return text + "..."


def generate() -> Path | None:
    new_skins = db.get_new_skins()
    if not new_skins:
        print("[周报] 本次没有新增，跳过生成")
        return None

    # 按游戏分组
    by_game: dict[str, list] = {}
    for s in new_skins:
        by_game.setdefault(s["game"], []).append(s)
    games = sorted(by_game.keys(), key=lambda g: len(by_game[g]), reverse=True)

    # 预下载缩略图
    print(f"[周报] 本次新增 {len(new_skins)} 条，正在下载缩略图...")
    thumbs: dict[int, Image.Image | None] = {}
    for game in games:
        for s in by_game[game][:MAX_ITEMS_PER_GAME]:
            if s["image_url"]:
                thumbs[s["id"]] = _download_thumb(s["image_url"])

    # 计算画布高度
    HEADER_H = 200
    SECTION_HEADER_H = 60
    section_h = {}
    for g in games:
        n = min(len(by_game[g]), MAX_ITEMS_PER_GAME)
        rows = (n + THUMB_PER_ROW - 1) // THUMB_PER_ROW
        section_h[g] = SECTION_HEADER_H + rows * CARD_HEIGHT + rows * THUMB_GAP
    total_h = HEADER_H + sum(section_h.values()) + 80  # 底部留白

    img = Image.new("RGB", (WIDTH, total_h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # ========== 顶部标题区 ==========
    font_title = _load_font(38, bold=True)
    font_sub = _load_font(18)
    font_stat_num = _load_font(48, bold=True)
    font_stat_label = _load_font(14)

    draw.text((40, 30), "🎯 射击游戏皮肤周报", font=font_title, fill=TEXT_LIGHT)
    today = datetime.now().strftime("%Y-%m-%d")
    draw.text((40, 85), f"更新时间：{today}  ·  本次新增皮肤汇总", font=font_sub, fill=TEXT_MUTED)

    # 三个统计数字
    stat_x = [40, 340, 640]
    stat_labels = [
        (str(len(new_skins)), "本次新增"),
        (str(len(games)), "涉及游戏"),
        (str(sum(1 for s in new_skins if s.get("rarity"))), "带品质标注"),
    ]
    for x, (num, lab) in zip(stat_x, stat_labels):
        draw.text((x, 130), num, font=font_stat_num, fill=ACCENT)
        draw.text((x + 4, 185), lab, font=font_stat_label, fill=TEXT_MUTED)

    # 分隔线
    draw.line([(40, HEADER_H - 5), (WIDTH - 40, HEADER_H - 5)],
              fill=(51, 65, 85), width=1)

    # ========== 各游戏区块 ==========
    font_section = _load_font(24, bold=True)
    font_section_sub = _load_font(14)
    font_name = _load_font(13)
    font_rarity = _load_font(11, bold=True)

    y = HEADER_H + 20
    for g in games:
        items = by_game[g][:MAX_ITEMS_PER_GAME]
        total_new_for_game = len(by_game[g])

        # 区块标题
        draw.rectangle([(40, y), (48, y + 32)], fill=ACCENT)
        draw.text((60, y + 2), g, font=font_section, fill=TEXT_LIGHT)
        cnt_txt = f"本次新增 {total_new_for_game} 条" + (f"（展示前 {len(items)}）" if total_new_for_game > len(items) else "")
        draw.text((60, y + 34), cnt_txt, font=font_section_sub, fill=TEXT_MUTED)
        y += SECTION_HEADER_H

        # 缩略图卡片
        for i, s in enumerate(items):
            row, col = divmod(i, THUMB_PER_ROW)
            card_x = 40 + col * (THUMB_SIZE + THUMB_GAP)
            card_y = y + row * (CARD_HEIGHT + THUMB_GAP)

            # 卡片底
            draw.rounded_rectangle(
                [(card_x, card_y), (card_x + THUMB_SIZE, card_y + CARD_HEIGHT)],
                radius=8, fill=CARD_BG,
            )

            # 缩略图
            thumb = thumbs.get(s["id"])
            if thumb:
                img.paste(thumb, (card_x, card_y), thumb)
            else:
                draw.text((card_x + 60, card_y + THUMB_SIZE // 2 - 8),
                          "无图", font=font_sub, fill=(100, 116, 139))

            # 名字（一行截断）
            name = _text_wrap(draw, s["name"], font_name, THUMB_SIZE - 12)
            draw.text((card_x + 6, card_y + THUMB_SIZE + 6),
                      name, font=font_name, fill=TEXT_LIGHT)

            # 品质小徽章
            if s.get("rarity"):
                r_txt = s["rarity"]
                r_color = s.get("rarity_color") or "#64748b"
                # hex → rgb
                try:
                    rc = tuple(int(r_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
                except Exception:
                    rc = (100, 116, 139)
                tw = draw.textlength(r_txt, font=font_rarity)
                bx, by_ = card_x + 6, card_y + THUMB_SIZE + 28
                draw.rounded_rectangle(
                    [(bx, by_), (bx + tw + 12, by_ + 18)],
                    radius=3, fill=rc,
                )
                draw.text((bx + 6, by_ + 2), r_txt, font=font_rarity, fill=(255, 255, 255))

        rows = (len(items) + THUMB_PER_ROW - 1) // THUMB_PER_ROW
        y += rows * (CARD_HEIGHT + THUMB_GAP) + 20

    # ========== 页脚 ==========
    font_foot = _load_font(12)
    draw.text((40, total_h - 40),
              "数据来源：Steam 市场 / valorant-api.com / fortnite-api.com / Fandom 等公开数据源  ·  仅供个人调研学习",
              font=font_foot, fill=TEXT_MUTED)

    out = REPORT_DIR / f"weekly_{today}.png"
    img.save(out, "PNG", optimize=True)
    print(f"[周报] 已生成: {out}")
    return out


if __name__ == "__main__":
    generate()
