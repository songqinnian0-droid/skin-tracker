"""
导出数据库中的皮肤数据为 JSON，供前端 index.html 读取。
"""
import json
from pathlib import Path
from datetime import datetime
import db

OUT_PATH = Path(__file__).parent / "data.json"


def export():
    all_skins = db.get_all_skins()

    # 按 "category - game" 分组，如 "枪械皮肤-CS2"
    groups = {}
    # 记录每个分组下都有哪些品质（按游戏内官方顺序）
    rarities_by_group = {}

    # 每个游戏的品质从低到高排序（用于前端筛选器排列）
    RARITY_ORDER = {
        "CS2": ["消费级", "工业级", "军规级", "受限", "保密", "隐秘", "违禁", "非凡"],
        "Valorant": ["Select", "Deluxe", "Premium", "Exclusive", "Ultra"],
        "Fortnite": ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic",
                     "Icon Series", "Gaming Legends Series", "MARVEL SERIES", "DC SERIES",
                     "Star Wars Series", "Slurp Series", "Frozen Series", "Lava Series",
                     "DARK SERIES", "Shadow Series", "Unattainable"],
        "Apex": ["Common", "Rare", "Epic", "Legendary", "Mythic"],
    }

    for s in all_skins:
        key = f"{s['category']}-{s['game']}"
        groups.setdefault(key, []).append({
            "name": s["name"],
            "image_url": s["image_url"],
            "source_url": s["source_url"],
            "first_seen": s["first_seen"],
            "is_new": bool(s["is_new"]),
            "rarity": s.get("rarity", "") or "",
            "rarity_color": s.get("rarity_color", "") or "",
        })
        # 收集品质集合
        r = s.get("rarity") or ""
        if r:
            rarities_by_group.setdefault(key, {})[r] = s.get("rarity_color") or ""

    # 每个分组的品质按游戏官方顺序排列
    rarity_lists = {}
    for key, rmap in rarities_by_group.items():
        game = key.split("-", 1)[1]
        order = RARITY_ORDER.get(game, [])
        # 已知顺序里的按顺序，未在列表里的追加在后
        sorted_rarities = [r for r in order if r in rmap] + \
                          [r for r in rmap if r not in order]
        rarity_lists[key] = [
            {"name": r, "color": rmap[r]} for r in sorted_rarities
        ]

    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(all_skins),
        "new_count": sum(1 for s in all_skins if s["is_new"]),
        "groups": groups,
        "rarities": rarity_lists,
    }

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"已导出 {len(all_skins)} 条到 {OUT_PATH}")


if __name__ == "__main__":
    export()
