"""
Valorant 皮肤爬虫
数据源：valorant-api.com（社区维护的公开 API，无需 key）

说明：
- Valorant 商业化外观只有：枪械皮肤（含刀）、Buddy 挂件、玩家卡、喷漆、终结动画
  没有传统意义的"角色时装"（英雄外观不卖）
- 本爬虫只抓"枪械皮肤"（含刀）
- 分类依据：assetPath 字段包含 "/Guns/" = 枪，"/Melee/" = 刀
- 过滤掉默认/无图皮肤
- "新上"判定由 db.py 的 diff 逻辑负责：全量入库后，下次跑新出现的会自动标 NEW
- 品质：通过 contentTierUuid 映射到 Select/Deluxe/Premium/Exclusive/Ultra
"""
import requests

BASE = "https://valorant-api.com/v1"
HEADERS = {"User-Agent": "skin-tracker/1.0"}

# 默认皮肤名关键词，直接排除
_EXCLUDE_KEYWORDS = ("Standard", "Random Favorite Skin")


def _fetch_json(url: str):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])


def _load_tier_map() -> dict:
    """
    构建 contentTierUuid → (品质名, 颜色) 的映射
    Valorant 品质从低到高：Select（青）→ Deluxe（绿）→ Premium（紫）→ Exclusive（金）→ Ultra（红）
    """
    try:
        tiers = _fetch_json(f"{BASE}/contenttiers")
    except Exception:
        return {}
    m = {}
    for t in tiers:
        # highlightColor 是 8 位 hex（含 alpha），取前 6 位作为 #RRGGBB
        hc = (t.get("highlightColor") or "")[:6]
        color = f"#{hc}" if hc else ""
        m[t["uuid"]] = (t.get("devName", ""), color)
    return m


def fetch(limit: int = None) -> list[dict]:
    """
    拉取 Valorant 全部枪械皮肤（含刀皮）
    """
    results = []
    tier_map = _load_tier_map()

    try:
        skins = _fetch_json(f"{BASE}/weapons/skins")
    except Exception as e:
        print(f"  [Valorant] 请求失败: {e}")
        return results

    for s in skins:
        name = (s.get("displayName") or "").strip()
        if not name:
            continue
        if any(kw in name for kw in _EXCLUDE_KEYWORDS):
            continue

        icon = s.get("displayIcon")
        if not icon:
            continue

        asset_path = (s.get("assetPath") or "").lower()
        if "/melee/" in asset_path:
            weapon_type = "刀"
        elif "/guns/" in asset_path:
            weapon_type = "枪"
        else:
            weapon_type = "枪"

        tier_uuid = s.get("contentTierUuid")
        rarity, rarity_color = tier_map.get(tier_uuid, ("", ""))

        results.append({
            "game": "Valorant",
            "category": "枪械皮肤",
            "name": name,
            "image_url": icon,
            "source_url": "https://playvalorant.com/",
            "rarity": rarity,
            "rarity_color": rarity_color,
            "_subtype": weapon_type,
        })

    if limit:
        results = results[-limit:]

    print(f"  [Valorant] 抓到 {len(results)} 条（枪械皮肤，含刀皮）")
    return results


if __name__ == "__main__":
    items = fetch()
    from collections import Counter
    print(f"\n总数: {len(items)}")
    print("品质分布:", Counter(i["rarity"] for i in items))
