# -*- coding: utf-8 -*-
"""_reveal_origin 的自检（#26：任务收尾把 Origin 窗口显示出来）。

    python test_reveal.py

用假的 originpro 替身跑分支，不连 Origin、不动任何真实数据：
未连接跳过 / 已连接显示并读回 / 节流 / force 绕过 / set_show 抛错如实返回。
"""
import io
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])


class FakeApp:
    """假 originpro 模块：记录 set_show 调用，get_show 返回可控状态。"""

    def __init__(self, visible_after=True):
        self.calls = []
        self.visible = False
        self.visible_after = visible_after

    def set_show(self, show=True):
        self.calls.append(show)
        if show:
            self.visible = self.visible_after

    def get_show(self):
        return self.visible


class BadApp(FakeApp):
    def set_show(self, show=True):
        raise RuntimeError("LT_evaluate failed")


def main():
    import origin_engine as eng

    # 1) 未连接：跳过，绝不为了显示去连接/新起实例
    eng._connected, eng._origin_app = False, None
    r = eng._reveal_origin(force=True)
    assert r["ok"] and r["skipped"] and r["reason"] == "not_connected", r

    # 2) 已连接（窗口隐藏）：显示 + @VIS 读回
    app = FakeApp(visible_after=True)
    eng._connected, eng._origin_app = True, app
    eng._reveal_at = 0.0
    r = eng._reveal_origin(force=True)
    assert app.calls == [True], app.calls
    assert r["ok"] and r["revealed"] is True, r
    assert r["visible_before"] is False and r["visible_after"] is True, r

    # 3) 节流：紧接着的非 force 调用不再动窗口
    r2 = eng._reveal_origin(force=False, throttle_seconds=600)
    assert r2["skipped"] and r2["reason"] == "throttled", r2
    assert app.calls == [True], app.calls

    # 4) force 绕过节流
    r3 = eng._reveal_origin(force=True, throttle_seconds=600)
    assert not r3.get("skipped") and app.calls == [True, True], (r3, app.calls)

    # 5) 读回仍为隐藏：如实报 revealed=False，不谎报成功
    app2 = FakeApp(visible_after=False)
    eng._connected, eng._origin_app = True, app2
    r4 = eng._reveal_origin(force=True)
    assert r4["ok"] and r4["revealed"] is False and r4["visible_after"] is False, r4

    # 6) set_show 抛错：返回 reveal_failed + 替代动作
    eng._origin_app = BadApp()
    r5 = eng._reveal_origin(force=True)
    assert r5["ok"] is False and r5["error_code"] == "reveal_failed", r5
    assert "origin_labtalk" in r5["hint"], r5

    # 7) 公开出口存在且被 COM 线程装饰（release 顺带显示、退出兜底都靠它）
    assert callable(eng.reveal) and hasattr(eng, "_reveal_at"), "engine.reveal 缺失"

    eng._connected, eng._origin_app = False, None
    print("test_reveal: 7/7 PASS")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
