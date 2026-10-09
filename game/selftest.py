"""Самопроверка без экрана: python main.py --selftest итог.txt.

Пока окна нет, проверяется ядро: правила обоих вариантов, фиксация хода хэшем и матчи
сильного ИИ против ботов с привычками. Итог пишется в файл (собранный exe - без консоли).
"""
import time
import traceback


def selftest(out_path):
    lines = []
    code = 0
    try:
        import aikit
        from game.ai.arena import run, summary
        from game.core.rules import beats
        from game.version import VERSION

        lines.append(f"RockPaperAi {VERSION} самопроверка (aikit {aikit.__version__})")
        for k in (3, 5):
            for m in range(k):
                if sum(beats(a, m, k) for a in range(k)) != (k - 1) // 2:
                    raise RuntimeError(f"правила на {k} знаков нарушены")
        lines.append("правила: 3 и 5 знаков, каждый знак бьёт половину остальных")
        for bot in ("cycle", "wsls", "repeat", "random"):
            t0 = time.time()
            s = summary(run("strong", bot, 2, 100, 1, 3))
            lines.append(f"сильный ИИ против «{bot}»: побед ИИ {s['all']['win']:.2f}, "
                         f"после 30-го раунда {s['after30']['win']:.2f}, {time.time() - t0:.2f} с")
            if bot in ("cycle", "wsls") and s["after30"]["win"] < 0.9:
                raise RuntimeError(f"ИИ не поймал привычку «{bot}»")
        lines.append("ИТОГ: работает")
    except Exception:  # noqa: BLE001 - любая ошибка должна попасть в файл
        lines.append("ИТОГ: ошибка")
        lines.append(traceback.format_exc())
        code = 1
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return code
