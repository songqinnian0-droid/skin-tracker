"""
CS2 皮肤爬虫
主数据源：ByMykel/CSGO-API（GitHub 上社区维护的完整 CS2 皮肤数据库，JSON 格式，无限流）
备用数据源：Steam 市场搜索接口（易 429 限流，仅作降级）
"""
import requests
import time
from urllib.parse import quote

# 主数据源：ByMykel 维护的 CS2 完整皮肤 JSON（每日自动更新）
BYMYKEL_SKINS = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/zh-CN/skins.json"
BYMYKEL_AGENTS = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/zh-CN/agents.json"

# 备用：Steam 市场
STEAM_SEARCH_URL = "https://steamcommunity.com/market/search/render/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36",
    "Accept": "application/json",
}


def _classify(item_name: str) -> str:
    """
    根据 Steam item 名称粗略分类。
    Steam 上 CS2 大部分是枪械皮肤；手套/贴纸/探员另算。
    - 探员皮肤 = 时装皮肤
    - 手套 = 时装皮肤（视为角色装扮）
    - 其他（步枪/手枪/刀）= 枪械皮肤
    """
    lower = item_name.lower()
    if "agent" in lower or "sticker" in lower:
        return "时装皮肤"
    if "gloves" in lower or "wraps" in lower or "hand" in lower:
        return "时装皮肤"
    return "枪械皮肤"


def _fetch_from_bymykel(limit: int) -> list[dict]:
    """从 ByMykel 的 GitHub JSON 拉数据（稳定，推荐）"""
    results = []

    # 枪械皮肤
    try:
        r = requests.get(BYMYKEL_SKINS, headers=HEADERS, timeout=30)
        r.raise_for_status()
        skins = r.json()
        skins = sorted(skins, key=lambda x: x.get("id", ""), reverse=True)
        for s in skins[:limit]:
            name = s.get("name", "").strip()
            if not name or "★" in name and "Vanilla" in name:
                continue
            rarity_obj = s.get("rarity") or {}
            results.append({
                "game": "CS2",
                "category": "枪械皮肤",
                "name": name,
                "image_url": s.get("image", ""),
                "source_url": f"https://steamcommunity.com/market/listings/730/{quote(name)}",
                "rarity": rarity_obj.get("name", "") if isinstance(rarity_obj, dict) else "",
                "rarity_color": rarity_obj.get("color", "") if isinstance(rarity_obj, dict) else "",
            })
    except Exception as e:
        print(f"  [CS2] 枪械皮肤(ByMykel)失败: {e}")

    # 探员（时装类）
    try:
        r = requests.get(BYMYKEL_AGENTS, headers=HEADERS, timeout=30)
        r.raise_for_status()
        agents = r.json()
        agents = sorted(agents, key=lambda x: x.get("id", ""), reverse=True)
        for a in agents[:limit // 2]:
            name = a.get("name", "").strip()
            if not name:
                continue
            rarity_obj = a.get("rarity") or {}
            results.append({
                "game": "CS2",
                "category": "时装皮肤",
                "name": name + "（探员）",
                "image_url": a.get("image", ""),
                "source_url": f"https://steamcommunity.com/market/listings/730/{quote(name)}",
                "rarity": rarity_obj.get("name", "") if isinstance(rarity_obj, dict) else "",
                "rarity_color": rarity_obj.get("color", "") if isinstance(rarity_obj, dict) else "",
            })
    except Exception as e:
        print(f"  [CS2] 探员(ByMykel)失败: {e}")

    return results


def fetch(limit: int = 80) -> list[dict]:
    """
    拉取 CS2 皮肤。优先用 ByMykel 数据源（稳定），失败时降级 Steam 市场。
    """
    results = _fetch_from_bymykel(limit)
    if results:
        print(f"  [CS2] 抓到 {len(results)} 条 (数据源: ByMykel)")
        return results

    # 降级：Steam 市场（易 429）
    print(f"  [CS2] 主数据源无数据，尝试 Steam 市场...")
    time.sleep(2)
    params = {
        "appid": 730, "norender": 1, "count": min(limit, 50),
        "sort_column": "quantity", "sort_dir": "desc",
    }
    try:
        r = requests.get(STEAM_SEARCH_URL, params=params,
                         headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        for item in data.get("results", []):
            name = item.get("name", "").strip()
            if not name:
                continue
            icon = item.get("asset_description", {}).get("icon_url", "")
            image_url = f"https://community.cloudflare.steamstatic.com/economy/image/{icon}/360fx360f" if icon else ""
            results.append({
                "game": "CS2",
                "category": _classify(name),
                "name": name,
                "image_url": image_url,
                "source_url": f"https://steamcommunity.com/market/listings/730/{quote(item.get('hash_name', name))}",
            })
    except Exception as e:
        print(f"  [CS2] Steam 备用源也失败: {e}")

    print(f"  [CS2] 抓到 {len(results)} 条")
    return results


if __name__ == "__main__":
    for x in fetch(10):
        print(x["category"], "|", x["name"])
