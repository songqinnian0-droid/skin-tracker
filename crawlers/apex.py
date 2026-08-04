"""
Apex Legends 皮肤爬虫
数据源：apexlegends.fandom.com (MediaWiki API)
策略：
  Apex Wiki 天然按品质 × 类型分类：
    Category:{Common|Rare|Epic|Legendary|Mythic} {legend|weapon} skin images
  → 品质字段直接得到
分类映射：
  legend skin  → 时装皮肤（英雄皮肤 = 角色时装）
  weapon skin  → 枪械皮肤
"""
import re
import requests

API = "https://apexlegends.fandom.com/api.php"
HEADERS = {"User-Agent": "skin-tracker/1.0"}

RARITIES = ["Common", "Rare", "Epic", "Legendary", "Mythic"]
RARITY_COLOR = {
    "Common": "#9e9e9e",
    "Rare": "#3b8fe1",
    "Epic": "#c745ff",
    "Legendary": "#f4a136",
    "Mythic": "#ff2b6d",
}
TYPE_MAP = {"legend": "时装皮肤", "weapon": "枪械皮肤"}


def _api(params):
    p = {**params, "format": "json"}
    r = requests.get(API, params=p, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def _get_files_paged(cat: str) -> list[str]:
    """分页拿分类里全部 File"""
    titles, cmcontinue = [], None
    while True:
        params = {"action": "query", "list": "categorymembers",
                  "cmtitle": cat, "cmlimit": 500, "cmtype": "file"}
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
        data = _api(params)
        titles += [m["title"] for m in data.get("query", {}).get("categorymembers", [])]
        cmcontinue = data.get("continue", {}).get("cmcontinue")
        if not cmcontinue:
            break
    return titles


def _get_image_urls(file_titles: list[str]) -> dict[str, str]:
    urls = {}
    for i in range(0, len(file_titles), 50):
        chunk = file_titles[i:i+50]
        data = _api({"action": "query", "titles": "|".join(chunk),
                     "prop": "imageinfo", "iiprop": "url"})
        for pg in data.get("query", {}).get("pages", {}).values():
            title = pg.get("title", "")
            ii = pg.get("imageinfo") or []
            if ii and title:
                urls[title] = ii[0].get("url", "")
    return urls


def _parse_name(file_title: str) -> str:
    """'File:Emerald Stone Bocek.png' → 'Emerald Stone Bocek'"""
    name = file_title.replace("File:", "")
    name = re.sub(r"\.(png|jpg|jpeg|webp|gif|svg)$", "", name, flags=re.I)
    return name.strip()


def fetch(limit: int = None) -> list[dict]:
    results = []
    all_files = []  # (file_title, category, rarity)

    for rarity in RARITIES:
        for tkey, category in TYPE_MAP.items():
            cat = f"Category:{rarity} {tkey} skin images"
            try:
                files = _get_files_paged(cat)
            except Exception as e:
                print(f"  [Apex] {cat} 失败: {e}")
                continue
            for f in files:
                all_files.append((f, category, rarity))

    print(f"  [Apex] 收集到 {len(all_files)} 个皮肤文件，正在批量拿图片链接...")
    url_map = _get_image_urls([f[0] for f in all_files])

    seen = set()  # 同名皮肤可能同时被归到多个品质分类，去重
    for f, category, rarity in all_files:
        name = _parse_name(f)
        if not name:
            continue
        key = (category, name)
        if key in seen:
            continue
        seen.add(key)
        img = url_map.get(f, "")
        if not img:
            continue
        results.append({
            "game": "Apex",
            "category": category,
            "name": name,
            "image_url": img,
            "source_url": f"https://apexlegends.fandom.com/wiki/{f.replace(' ', '_')}",
            "rarity": rarity,
            "rarity_color": RARITY_COLOR.get(rarity, ""),
        })

    if limit:
        results = results[-limit:]
    print(f"  [Apex] 抓到 {len(results)} 条")
    return results


if __name__ == "__main__":
    items = fetch()
    from collections import Counter
    print(Counter((i["category"], i["rarity"]) for i in items).most_common())
