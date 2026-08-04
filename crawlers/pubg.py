"""
PUBG 皮肤爬虫
数据源：pubg.fandom.com (MediaWiki API)
策略：
  1. 遍历 "Category:Weapon Skins" 下的所有武器子分类（AKM Skins / M416 Skins / ...）
  2. 每个武器分类里的 File 就是皮肤图，从文件名解析皮肤名
  3. 用 imageinfo 批量拿图片直链
说明：
  - PUBG Wiki 没有品质字段，rarity 留空
  - PUBG Wiki 只有武器皮肤，没有服装分类，所以只出"枪械皮肤"
"""
import re
import requests

API = "https://pubg.fandom.com/api.php"
HEADERS = {"User-Agent": "skin-tracker/1.0"}


def _api(params: dict):
    params = {**params, "format": "json"}
    r = requests.get(API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def _get_weapon_subcats() -> list[str]:
    """获取 Weapon Skins 下的所有武器子分类名"""
    data = _api({
        "action": "query", "list": "categorymembers",
        "cmtitle": "Category:Weapon Skins", "cmlimit": 500,
    })
    members = data.get("query", {}).get("categorymembers", [])
    # ns=14 是子分类
    return [m["title"] for m in members if m["ns"] == 14]


def _get_files_in_cat(cat_title: str) -> list[str]:
    """拿分类下所有 File:xxx"""
    data = _api({
        "action": "query", "list": "categorymembers",
        "cmtitle": cat_title, "cmlimit": 500, "cmtype": "file",
    })
    return [m["title"] for m in data.get("query", {}).get("categorymembers", [])]


def _get_image_urls(file_titles: list[str]) -> dict[str, str]:
    """批量拿图片直链。MediaWiki 单次可查最多 50 个 titles"""
    urls = {}
    for i in range(0, len(file_titles), 50):
        chunk = file_titles[i:i+50]
        data = _api({
            "action": "query", "titles": "|".join(chunk),
            "prop": "imageinfo", "iiprop": "url",
        })
        for pg in data.get("query", {}).get("pages", {}).values():
            title = pg.get("title", "")
            ii = pg.get("imageinfo") or []
            if ii and title:
                urls[title] = ii[0].get("url", "")
    return urls


def _parse_skin_name(file_title: str, weapon: str) -> str:
    """
    从 'File:Weapon skin Glory AKM.png' 解析出 '格洛丽亚 AKM'
    格式：'File:Weapon skin <皮肤名> <武器名>.<扩展名>'
    """
    name = file_title.replace("File:", "")
    name = re.sub(r"\.(png|jpg|jpeg|webp|gif)$", "", name, flags=re.I)
    # 去掉前缀 "Weapon skin "
    name = re.sub(r"^Weapon\s+skin\s+", "", name, flags=re.I)
    return name.strip()


def fetch(limit: int = None) -> list[dict]:
    results = []
    try:
        subcats = _get_weapon_subcats()
    except Exception as e:
        print(f"  [PUBG] 获取武器分类失败: {e}")
        return results

    print(f"  [PUBG] 发现 {len(subcats)} 个武器分类")
    total_files = []
    file_to_weapon = {}
    for cat in subcats:
        weapon = cat.replace("Category:", "").replace(" Skins", "")
        try:
            files = _get_files_in_cat(cat)
        except Exception as e:
            print(f"  [PUBG] {cat} 失败: {e}")
            continue
        for f in files:
            total_files.append(f)
            file_to_weapon[f] = weapon

    print(f"  [PUBG] 共找到 {len(total_files)} 个皮肤文件，正在批量拿图片链接...")
    url_map = _get_image_urls(total_files)

    for f in total_files:
        weapon = file_to_weapon[f]
        name = _parse_skin_name(f, weapon)
        if not name:
            continue
        img = url_map.get(f, "")
        if not img:
            continue
        results.append({
            "game": "PUBG",
            "category": "枪械皮肤",
            "name": name,
            "image_url": img,
            "source_url": f"https://pubg.fandom.com/wiki/{f.replace(' ', '_')}",
            "rarity": "",
            "rarity_color": "",
        })

    if limit:
        results = results[-limit:]
    print(f"  [PUBG] 抓到 {len(results)} 条")
    return results


if __name__ == "__main__":
    items = fetch()
    for x in items[:5]:
        print(x["name"], "|", x["image_url"])
