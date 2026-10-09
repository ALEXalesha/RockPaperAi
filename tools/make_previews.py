"""Кадры для README и списка игр: окно без экрана, матч в нескольких состояниях.

    python tools/make_previews.py [папка]     # по умолчанию docs/
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aikit import offscreen  # noqa: E402

offscreen.setup(force=True)
os.environ["ROCKPAPERAI_HOME"] = tempfile.mkdtemp(prefix="rockpaperai-previews-")


def main(out):
    from PySide6.QtWidgets import QApplication

    from aikit.host import make_window
    from game import APP_NAME, GAME_INFO, create_widget
    from game.ai.bots import make_bot

    os.makedirs(out, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    window, ctx = make_window(GAME_INFO, create_widget, APP_NAME, root=os.environ["ROCKPAPERAI_HOME"])
    window.resize(1280, 800)
    window.show()
    g = window.game
    shots = []

    def shot(name):
        app.processEvents()
        shots.append((window.grab(), name))

    def play(n, key="human", seed=1):
        bot = make_bot(key, g.session.k, seed=seed)
        for _ in range(n):
            if g.session.over:
                break
            g.on_sign(bot.move(g.session.match.history()))

    for theme_name in ("dark", "light"):
        ctx.set_theme(theme_name)
        sfx = "" if theme_name == "dark" else "_light"
        g.change("k", 3)
        g.change("length", 50)
        g.change("show_thoughts", True)
        g.change("peek", False)
        g.show_page("menu")
        shot(f"preview_menu{sfx}.png")
        g.start_match(seed=21)
        play(34, "human", 2)
        shot(f"preview_play{sfx}.png")
        play(50, "human", 2)
        shot(f"preview_review{sfx}.png")
        g.change("k", 5)
        g.start_match(seed=22)
        play(25, "wsls", 3)
        shot(f"preview_five{sfx}.png")
        g.change("k", 3)
        g.show_page("stats")
        shot(f"preview_stats{sfx}.png")
    ctx.set_theme("dark")
    window.resize(1280, 720)
    g.change("length", 100)
    g.start_match(seed=23)
    play(40, "wsls", 4)
    shot("preview.png")
    g.change("length", 100)
    for pix, name in shots:
        pix.save(os.path.join(out, name))
        print(name)
    g.shutdown()
    window.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs"))
