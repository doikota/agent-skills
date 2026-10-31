"""bundle.html に対する E2E テスト（タスクの追加・完了・削除と、その周辺の挙動）。

実行:  /usr/local/bin/python3 web/aosa-tasks/tests/test_e2e.py
依存:  Python Playwright（Chromium）のみ。pytest は不要（標準の unittest）。
外部ネットワーク（Google Fonts など）への通信はすべて遮断してテストする。
"""

import re
import sys
import unittest
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

BUNDLE = Path(__file__).resolve().parent.parent / "bundle.html"
URL = BUNDLE.as_uri()
SAMPLE_COUNT = 3  # 初回表示のサンプルタスク数（挑戦中 2 / 実った 1）


class TaskAppE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BUNDLE.exists():
            raise FileNotFoundError(f"{BUNDLE} がありません。先にバンドルしてください。")
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.context = None
        self.errors: list[str] = []
        self.open()
        expect(self.items()).to_have_count(SAMPLE_COUNT)

    def open(self, init_script: str | None = None, viewport: dict | None = None, clock: bool = False):
        """新しいコンテキスト（= localStorage が空）でページを開き直す。"""
        if self.context:
            self.context.close()
        self.context = self.browser.new_context(reduced_motion="reduce", viewport=viewport)
        # 外部通信（Google Fonts など）はすべて遮断する
        self.context.route(re.compile(r"^(?!file:).*"), lambda route: route.abort())
        if init_script:
            self.context.add_init_script(init_script)
        self.page: Page = self.context.new_page()
        if clock:
            self.page.clock.install()
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.on(
            "console",
            lambda m: self.errors.append(f"console.error: {m.text}")
            if m.type == "error" and "net::ERR_FAILED" not in m.text
            else None,
        )
        self.page.goto(URL)

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [], "ページで JavaScript エラーが発生しました")

    # ---- helpers -------------------------------------------------------
    def items(self):
        return self.page.locator("li.item")

    def item(self, text: str):
        return self.items().filter(has_text=text)

    def stat(self, label: str):
        return self.page.locator(".stats span", has_text=label).locator("b")

    def labels(self) -> list[str]:
        """表示中のタスク本文（サンプル表示や日時を除く）"""
        return [t.split("\n")[0].removesuffix("サンプル") for t in self.items().locator("label").all_inner_texts()]

    def show(self, name: str):
        self.page.get_by_role("button", name=re.compile(f"^{name}")).click()

    def delete(self, text: str):
        self.page.get_by_role("button", name=f"「{text}」を削除").click()

    def add_task(self, text: str, via_enter: bool = False):
        field = self.page.get_by_placeholder("次に挑むことを書く")
        field.fill(text)
        if via_enter:
            field.press("Enter")
        else:
            self.page.get_by_role("button", name="追加", exact=True).click()

    # ---- 追加 ----------------------------------------------------------
    def test_add_task_with_button(self):
        self.add_task("E2E: ボタンで追加したタスク")

        expect(self.items()).to_have_count(SAMPLE_COUNT + 1)
        expect(self.items().first).to_contain_text("E2E: ボタンで追加したタスク")
        expect(self.items().first).not_to_have_class(re.compile(r"\bdone\b"))
        expect(self.page.get_by_placeholder("次に挑むことを書く")).to_have_value("")
        expect(self.stat("挑戦中")).to_have_text("3")
        expect(self.stat("達成率")).to_have_text("25%")

    def test_add_task_with_enter(self):
        self.add_task("E2E: Enter で追加", via_enter=True)
        expect(self.items().first).to_contain_text("E2E: Enter で追加")
        expect(self.items()).to_have_count(SAMPLE_COUNT + 1)

    def test_add_button_disabled_for_blank_input(self):
        button = self.page.get_by_role("button", name="追加", exact=True)
        expect(button).to_be_disabled()
        self.page.get_by_placeholder("次に挑むことを書く").fill("   ")
        expect(button).to_be_disabled()
        self.page.get_by_placeholder("次に挑むことを書く").press("Enter")
        expect(self.items()).to_have_count(SAMPLE_COUNT)

    def test_added_task_survives_reload(self):
        self.add_task("E2E: 再読み込み後も残る")
        self.page.reload()
        expect(self.item("E2E: 再読み込み後も残る")).to_have_count(1)
        expect(self.items()).to_have_count(SAMPLE_COUNT + 1)

    # ---- 完了 ----------------------------------------------------------
    def test_complete_and_uncomplete_task(self):
        self.add_task("E2E: 完了させるタスク")
        row = self.item("E2E: 完了させるタスク")
        checkbox = row.get_by_role("checkbox")

        checkbox.check()
        expect(checkbox).to_be_checked()
        expect(row).to_have_class(re.compile(r"\bdone\b"))
        expect(self.stat("実った")).to_have_text("2")
        expect(self.stat("挑戦中")).to_have_text("2")
        expect(self.stat("達成率")).to_have_text("50%")

        # 「実った」フィルタに表示され、「挑戦中」からは消える
        self.page.get_by_role("button", name=re.compile("^実った")).click()
        expect(self.item("E2E: 完了させるタスク")).to_have_count(1)
        self.page.get_by_role("button", name=re.compile("^挑戦中")).click()
        expect(self.item("E2E: 完了させるタスク")).to_have_count(0)

        # 未完了に戻す
        self.page.get_by_role("button", name=re.compile("^すべて")).click()
        row.get_by_role("checkbox").uncheck()
        expect(row).not_to_have_class(re.compile(r"\bdone\b"))
        expect(self.stat("実った")).to_have_text("1")

    def test_click_label_toggles_completion(self):
        row = self.item("企画書のたたき台をチームに共有する")
        row.locator("label").click()
        expect(row.get_by_role("checkbox")).to_be_checked()

    # ---- 削除 ----------------------------------------------------------
    def test_delete_task(self):
        self.add_task("E2E: 削除するタスク")
        self.page.get_by_role("button", name="「E2E: 削除するタスク」を削除").click()

        expect(self.item("E2E: 削除するタスク")).to_have_count(0)
        expect(self.items()).to_have_count(SAMPLE_COUNT)
        expect(self.page.get_by_role("status")).to_contain_text("削除しました")

        # 削除は再読み込み後も維持される
        self.page.reload()
        expect(self.item("E2E: 削除するタスク")).to_have_count(0)

    def test_undo_delete_restores_position(self):
        texts_before = self.items().locator("label").all_inner_texts()
        target = "企画書のたたき台をチームに共有する"
        self.page.get_by_role("button", name=f"「{target}」を削除").click()
        expect(self.items()).to_have_count(SAMPLE_COUNT - 1)

        self.page.get_by_role("button", name="元に戻す").click()
        expect(self.items()).to_have_count(SAMPLE_COUNT)
        expect(self.page.get_by_role("status")).to_have_count(0)
        self.assertEqual(self.items().locator("label").all_inner_texts(), texts_before)

    def test_delete_all_shows_empty_state(self):
        for _ in range(SAMPLE_COUNT):
            self.items().first.locator("button.del").click()
        expect(self.items()).to_have_count(0)
        expect(self.page.locator(".empty")).to_contain_text("タスクはまだありません")
        expect(self.stat("達成率")).to_have_text("0%")


    def test_consecutive_deletes_can_all_be_undone(self):
        before = self.labels()
        self.delete("朝いちばんに今週の目標を3つ書き出す")
        self.delete("まだ試していない方法をひとつ選んで挑む")
        expect(self.items()).to_have_count(SAMPLE_COUNT - 2)
        expect(self.page.get_by_role("status")).to_contain_text("2件削除しました")

        self.page.get_by_role("button", name="元に戻す").click()
        expect(self.items()).to_have_count(SAMPLE_COUNT)
        self.assertEqual(self.labels(), before)

    def test_undo_is_persisted(self):
        before = self.labels()
        self.delete("企画書のたたき台をチームに共有する")
        self.page.get_by_role("button", name="元に戻す").click()
        self.page.reload()
        expect(self.items()).to_have_count(SAMPLE_COUNT)
        self.assertEqual(self.labels(), before)

    def test_delete_is_confirmed_after_5_seconds(self):
        self.open(clock=True)
        self.delete("企画書のたたき台をチームに共有する")
        expect(self.page.get_by_role("status")).to_be_visible()

        self.page.clock.run_for(4000)
        expect(self.page.get_by_role("status")).to_be_visible()
        self.page.clock.run_for(1500)
        expect(self.page.get_by_role("status")).to_have_count(0)
        expect(self.items()).to_have_count(SAMPLE_COUNT - 1)

    def test_delete_from_filtered_view(self):
        self.show("実った")
        self.delete("朝いちばんに今週の目標を3つ書き出す")
        expect(self.page.locator(".empty")).to_contain_text("まだ実ったタスクはありません")
        expect(self.stat("実った")).to_have_text("0")
        self.show("すべて")
        expect(self.items()).to_have_count(SAMPLE_COUNT - 1)

    # ---- 保存 ----------------------------------------------------------
    def test_completion_is_persisted(self):
        row = self.item("企画書のたたき台をチームに共有する")
        row.get_by_role("checkbox").check()
        self.page.reload()
        expect(self.item("企画書のたたき台をチームに共有する").get_by_role("checkbox")).to_be_checked()
        expect(self.stat("実った")).to_have_text("2")

    # ---- 絞り込み ------------------------------------------------------
    def test_adding_while_showing_done_switches_to_all(self):
        self.show("実った")
        self.add_task("E2E: 実った表示中に追加")
        expect(self.page.get_by_role("button", name=re.compile("^すべて"))).to_have_attribute("aria-pressed", "true")
        expect(self.items().first).to_contain_text("E2E: 実った表示中に追加")

    def test_filter_empty_messages(self):
        for row in self.items().get_by_role("checkbox").all():
            row.check()
        self.show("挑戦中")
        expect(self.items()).to_have_count(0)
        expect(self.page.locator(".empty")).to_contain_text("挑戦中のタスクはありません")
        expect(self.stat("達成率")).to_have_text("100%")

    # ---- 入力 ----------------------------------------------------------
    def test_input_is_trimmed_and_html_is_shown_as_text(self):
        self.add_task("  <b>E2E</b> & <script>x</script>  ")
        self.assertEqual(self.labels()[0], "<b>E2E</b> & <script>x</script>")
        expect(self.items().first.locator("b, script")).to_have_count(0)

    def test_input_max_length(self):
        self.add_task("あ" * 200)
        self.assertEqual(len(self.labels()[0]), 120)

    # ---- 保存データの異常系 --------------------------------------------
    def test_broken_storage_falls_back_to_samples(self):
        for raw in ["{}", "not json", "null", '[{"id": 1}]']:
            with self.subTest(raw=raw):
                self.open(init_script=f"localStorage.setItem('aosa-tasks.v1', {raw!r})")
                expect(self.page.get_by_placeholder("次に挑むことを書く")).to_be_visible()
                expected = 0 if raw.startswith("[") else SAMPLE_COUNT  # 配列なら不正な要素だけ除く
                expect(self.items()).to_have_count(expected)
                self.add_task("E2E: 復旧後に追加")
                expect(self.items()).to_have_count(expected + 1)

    def test_works_without_storage(self):
        self.open(init_script="Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked') } })")
        expect(self.items()).to_have_count(SAMPLE_COUNT)
        self.add_task("E2E: 保存なしで追加")
        self.item("E2E: 保存なしで追加").get_by_role("checkbox").check()
        self.delete("E2E: 保存なしで追加")
        expect(self.items()).to_have_count(SAMPLE_COUNT)

    # ---- 表示・操作性 --------------------------------------------------
    def test_page_head(self):
        self.assertEqual(self.page.title(), "青さで、挑む。タスク")
        expect(self.page.locator('link[href^="https://fonts.googleapis.com/css2"]')).to_have_count(1)
        expect(self.page.locator('meta[name="claude:viewport-fit-sides"]')).to_have_count(1)

    def test_no_horizontal_scroll_on_phone(self):
        self.open(viewport={"width": 375, "height": 800})
        self.add_task("E2E:" + "とても長いタスク名" * 12)
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 375)

    def test_keyboard_operation(self):
        field = self.page.get_by_placeholder("次に挑むことを書く")
        field.fill("E2E: キーボードで操作")
        field.press("Enter")
        checkbox = self.item("E2E: キーボードで操作").get_by_role("checkbox")
        checkbox.focus()
        self.page.keyboard.press("Space")
        expect(checkbox).to_be_checked()
        self.page.keyboard.press("Tab")
        expect(self.page.get_by_role("button", name="「E2E: キーボードで操作」を削除")).to_be_focused()
        self.page.keyboard.press("Enter")
        expect(self.item("E2E: キーボードで操作")).to_have_count(0)

if __name__ == "__main__":
    sys.exit(0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 1)
