"""
Fortnite 皮肤爬虫
数据源：fortnite-api.com (免鉴权 JSON)
映射：Wrap(武器包装) → 枪械皮肤；Outfit(服装) → 时装皮肤
"""
import requests

URL = "https://fortnite-api.com/v2/cosmetics/br"
HEADERS = {"User-Agent": "skin-tracker/1.0"}

# type.backendValue → 我们的分类
TYPE_MAP = {
    "AthenaCharacter": "时装皮肤",   # Outfit 服装
}

# Fortnite 品质颜色（对齐游戏内配色）
RARITY_COLOR = {
    "Common": "#9e9e9e",
    "Uncommon": "#5ac53a",
    "Rare": "#3b8fe1",
    "Epic": "#c745ff",
    "Legendary": "#f4a136",
    "Mythic": "#ffe97a",
    "Icon Series": "#00e5ff",
    "MARVEL SERIES": "#ed1d24",
    "DC SERIES": "#3a63a8",
    "Gaming Legends Series": "#5b40a0",
    "Star Wars Series": "#e5bd45",
    "Slurp Series": "#00c9a8",
    "Frozen Series": "#a8dcff",
    "Lava Series": "#ff4500",
    "DARK SERIES": "#7c3aed",
    "Shadow Series": "#4b5563",
    "Unattainable": "#ec4899",
}


def fetch(limit: int = None) -> list[dict]:
    results = []
    try:
        r = requests.get(URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json().get("data", [])
    except Exception as e:
        print(f"  [Fortnite] 请求失败: {e}")
        return results

    for it in data:
        tb = (it.get("type") or {}).get("backendValue")
        category = TYPE_MAP.get(tb)
        if not category:
            continue
        name = (it.get("name") or "").strip()
        if not name:
            continue
        images = it.get("images") or {}
        img = images.get("icon") or images.get("smallIcon") or ""
        if not img:
            continue
        rarity_obj = it.get("rarity") or {}
        rarity_name = rarity_obj.get("displayValue", "")
        results.append({
            "game": "Fortnite",
            "category": category,
            "name": name,
            "image_url": img,
            "source_url": f"https://fortnite-api.com/images/cosmetics/br/{it.get('id','')}/icon.png",
            "rarity": rarity_name,
            "rarity_color": RARITY_COLOR.get(rarity_name, "#64748b"),
        })

    if limit:
        results = results[-limit:]
    print(f"  [Fortnite] 抓到 {len(results)} 条")
    return results


if __name__ == "__main__":
    from collections import Counter
    items = fetch()
    print(Counter(i["category"] for i in items))
    print(Counter(i["rarity"] for i in items).most_common(10))
