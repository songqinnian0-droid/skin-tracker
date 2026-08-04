"""
Rainbow Six Siege 皮肤爬虫
数据源：rainbowsix.fandom.com
策略：从总页 "Weapon Skins (Siege)" 一次性拿 1000+ 张皮肤图
  文件命名规律：<皮肤名>_<武器名>_Skin.png
说明：
  - R6 Wiki 无品质字段，rarity 留空
  - 只抓武器皮肤（Uniforms/干员时装数据太散，性价比低）
"""
import re
import requests

API = "https://rainbowsix.fandom.com/api.php"
HEADERS = {"User-Agent": "skin-tracker/1.0"}

# 排除的非皮肤图标（页面上会混入 UI 图标）
_EXCLUDE = re.compile(r"(icon|logo|units|renown|credits|placeholder)", re.I)


def _api(params):
    p = {**params, "format": "json"}
    r = requests.get(API, params=p, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def _get_image_urls(file_titles: list[str]) -> dict[str, str]:
    """
    返回 dict: 归一化的 title（空格版）→ url
    MediaWiki 会把下划线转空格，需要用返回的 title 匹配
    """
    urls = {}
    for i in range(0, len(file_titles), 50):
        chunk = file_titles[i:i+50]
        try:
            data = _api({"action": "query", "titles": "|".join(chunk),
                         "prop": "imageinfo", "iiprop": "url"})
            for pg in data.get("query", {}).get("pages", {}).values():
                title = pg.get("title", "")
                ii = pg.get("imageinfo") or []
                if ii and title:
                    urls[title] = ii[0].get("url", "")
        except Exception:
            continue
    return urls


def _parse_name(filename: str) -> str:
    """'Black_Ice_L85A2_Skin.png' → 'Black Ice L85A2'"""
    name = re.sub(r"\.(png|jpg|jpeg|webp|gif)$", "", filename, flags=re.I)
    name = re.sub(r"_?Skin$", "", name, flags=re.I)
    return name.replace("_", " ").strip()


def fetch(limit: int = None) -> list[dict]:
    results = []
    try:
        data = _api({"action": "parse", "page": "Weapon Skins (Siege)", "prop": "images"})
        images = data.get("parse", {}).get("images", [])
    except Exception as e:
        print(f"  [R6] 请求失败: {e}")
        return results

    # 过滤：文件名含 "_Skin" 的才是皮肤，且排除 UI 图标
    skin_files = [f for f in images
                  if re.search(r"_Skin\.", f, re.I) and not _EXCLUDE.search(f)]
    file_titles = [f"File:{f}" for f in skin_files]
    print(f"  [R6] 页面共 {len(images)} 张图，筛出皮肤图 {len(skin_files)} 张，批量拿链接...")

    url_map = _get_image_urls(file_titles)

    seen = set()
    for f in skin_files:
        name = _parse_name(f)
        if not name or name in seen:
            continue
        seen.add(name)
        # 用归一化的 title 查（下划线转空格）
        normalized = "File:" + f.replace("_", " ")
        img = url_map.get(normalized, "")
        if not img:
            continue
        results.append({
            "game": "R6",
            "category": "枪械皮肤",
            "name": name,
            "image_url": img,
            "source_url": "https://rainbowsix.fandom.com/wiki/Weapon_Skins_(Siege)",
            "rarity": "",
            "rarity_color": "",
        })

    if limit:
        results = results[-limit:]
    print(f"  [R6] 抓到 {len(results)} 条")
    return results


if __name__ == "__main__":
    for x in fetch()[:5]:
        print(x["name"], "|", x["image_url"])
