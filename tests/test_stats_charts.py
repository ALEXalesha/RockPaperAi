"""Графики статистики из общего aikit.charts (правило автора 10.10: графики во всех играх с ИИ).

Законы: на странице статистики есть графики aikit; без матчей - заглушки словами (не пустая
сетка); подписи целы (chart.clipped пуст) в обеих темах, на обоих языках, в широком и самом
узком окне; серии выигранных матчей считаются по итогам матчей."""
from aikit.charts import ChartCard, all_charts
from tests.test_ui import app, play_with_bot, win  # noqa: F401 - фикстуры окна


def labels_intact(app, win, g):
    for theme in ("dark", "light"):
        for lang in ("ru", "en"):
            win.ctx.set_theme(theme)
            win.ctx.set_lang(lang)
            for width in (1280, 3840, win.minimumWidth()):
                win.resize(width, 800)
                app.processEvents()
                for c in all_charts(g.stats):
                    c.grab()
                    assert c.clipped == [], (theme, lang, width, c.title, c.clipped)
                    assert c.overlaps() == [], (theme, lang, width, c.title, c.overlaps())
    win.ctx.set_theme("dark")
    win.ctx.set_lang("ru")
    win.resize(1280, 800)


def test_stats_page_has_aikit_charts_and_stubs_without_matches(app, win):
    g = win.game
    g.show_page("stats")
    charts = all_charts(g.stats)
    assert len(charts) >= 4 and all(isinstance(c, ChartCard) for c in charts)
    st = g.stats
    for c in (st.chart_matches, st.chart_streak, st.chart_levels):
        c.grab()
        assert c.shown_empty and c.empty_text, c.title
    st.chart_ai.grab()
    assert not st.chart_ai.shown_empty            # паспорт есть и без матчей
    labels_intact(app, win, g)


def test_charts_with_matches_show_data_and_keep_labels(app, win):
    g = win.game
    g.change("length", 50)
    for level, seed, bot in (("strong", 1, "cycle"), ("strong", 2, "cycle"), ("novice", 3, "random")):
        g.change("level", level)
        g.start_match(seed=seed)
        play_with_bot(g, bot, seed)
    g.show_page("stats")
    st = g.stats
    for c in all_charts(st):
        c.grab()
        assert not c.shown_empty, c.title
    hist = g.match_history()
    wins = [m["wins"] > m["losses"] for m in hist]
    run, now = 0, []
    for w in wins:
        run = run + 1 if w else 0
        now.append(float(run))
    assert [y for _, y in st.chart_streak.points] == now
    assert [y for _, y in st.chart_streak.second] == [max(now[:i + 1]) for i in range(len(now))]
    labels_intact(app, win, g)


def test_streaks_of_matches_from_the_journal(app, win):
    """Серия - выигранные матчи подряд (раундов у вас больше, чем у ИИ); ничья и поражение рвут."""
    import json
    g = win.game
    rows = [(30, 10, 10), (25, 5, 20), (10, 30, 10), (15, 20, 15), (40, 0, 10), (31, 0, 19)]
    data = [{"k": 3, "level": "strong", "rounds": w + t + lo, "wins": w, "ties": t, "losses": lo} for w, t, lo in rows]
    with open(g.ctx.file("matches.json"), "w", encoding="utf-8") as f:
        json.dump(data, f)
    g.show_page("stats")
    st = g.stats
    assert [y for _, y in st.chart_streak.points] == [1, 2, 0, 0, 1, 2]
    assert [y for _, y in st.chart_streak.second] == [1, 2, 2, 2, 2, 2]


def test_abandoned_match_breaks_the_streak_even_when_you_led(app, win):
    """Брошенный матч в статистике - поражение при любом счёте (правило 1.0.2), и серия на
    графике тоже рвётся. В 1.0.3 график брал итог по счёту раундов: два брошенных матча,
    где вы вели 3:0 и 2:0, рисовал серией 2 и рекордом 2 при «0 побед» в таблице."""
    from tests.test_abandon import leave, win_rounds
    g = win.game
    g.change("level", "novice")
    g.change("length", 50)
    for seed, n in ((1, 3), (2, 2)):
        g.start_match(seed=seed)
        win_rounds(g, n)
        leave(app, g, "menu")
    e = g.ctx.stats.entry(g.session.stats_key())
    assert e["losses"] == 2 and e["best_streak"] == 0
    assert all(m.get("abandoned") for m in g.match_history())
    g.show_page("stats")
    st = g.stats
    assert [y for _, y in st.chart_streak.points] == [0, 0]
    assert [y for _, y in st.chart_streak.second] == [0, 0]


def test_abandoned_match_in_the_journal_is_a_loss():
    from game.ui.widget import match_outcome
    m = {"k": 3, "level": "strong", "rounds": 4, "wins": 4, "ties": 0, "losses": 0}
    assert match_outcome(m) == "win"
    assert match_outcome(dict(m, abandoned=True)) == "loss"
