"""
主入口：跑一遍所有爬虫 → 写数据库 → 导出 JSON → 启动本地服务器打开网页
"""
import db
import export_json
import http.server
import socketserver
import threading
import webbrowser
import sys
from pathlib import Path
from crawlers import cs2, valorant, fortnite, pubg, apex, r6

# 已启用的爬虫列表。后续新增游戏在这里加一行即可。
# 注：The Finals Wiki 上没有真正的皮肤数据（只有武器演示截图），已移除。
CRAWLERS = [
    ("CS2", cs2.fetch),
    ("Valorant", valorant.fetch),
    ("Fortnite", fortnite.fetch),
    ("PUBG", pubg.fetch),
    ("Apex", apex.fetch),
    ("R6", r6.fetch),
]

PORT = 8765
WEB_DIR = Path(__file__).parent / "web"


def run_once():
    print("=" * 50)
    print("皮肤追踪器 - 开始运行")
    print("=" * 50)

    db.init_db()
    db.mark_all_as_old()  # 先把老数据清 is_new 标记

    total_new = 0
    for game_label, fetch_fn in CRAWLERS:
        print(f"\n>>> 正在爬取 {game_label} ...")
        try:
            items = fetch_fn()
        except Exception as e:
            print(f"  [{game_label}] 爬虫崩溃: {e}")
            continue

        new_in_game = 0
        for it in items:
            is_new = db.upsert_skin(
                game=it["game"],
                category=it["category"],
                name=it["name"],
                image_url=it.get("image_url", ""),
                source_url=it.get("source_url", ""),
                rarity=it.get("rarity", ""),
                rarity_color=it.get("rarity_color", ""),
            )
            if is_new:
                new_in_game += 1
        print(f"  [{game_label}] 本次新增 {new_in_game} 条")
        total_new += new_in_game

    print(f"\n本次共发现新皮肤：{total_new} 条")

    print("\n>>> 导出前端数据 ...")
    export_json.export()

    # 生成每周简报 PNG（若本次无新增会自动跳过）
    print("\n>>> 生成周报 PNG ...")
    try:
        import report
        report.generate()
    except Exception as e:
        print(f"[周报] 生成失败: {e}")


def serve():
    """启动本地小服务器，用浏览器打开网页"""
    import os
    os.chdir(WEB_DIR)

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # 静音日志

    try:
        with socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler) as httpd:
            url = f"http://127.0.0.1:{PORT}/index.html"
            print(f"\n本地服务器已启动：{url}")
            print("按 Ctrl+C 停止服务器\n")
            # 延迟 1 秒后自动开浏览器
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()
            httpd.serve_forever()
    except OSError as e:
        print(f"端口 {PORT} 被占用或启动失败: {e}")
        print(f"请手动关掉占用端口的程序，或改 main.py 里的 PORT 值")


if __name__ == "__main__":
    # 支持两种模式：
    #   python main.py        → 爬取 + 启动网页（默认，日常/首次用）
    #   python main.py fetch  → 只爬取，不启动网页（每周自动定时用）
    #   python main.py serve  → 只启动网页（数据已有时快速查看）
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "fetch"):
        run_once()
    if mode in ("all", "serve"):
        serve()
