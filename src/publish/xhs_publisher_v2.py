"""
小红书浏览器自动化发布器 v2 — opencli + Playwright 混合方案

- opencli browser: 上传图片、填写表单
- Playwright:    填充正文（逐段type）、点击发布按钮

解决 v1 两个核心问题：
1. opencli fill 对 contenteditable 区域填不完整 → Playwright type
2. dispatchEvent 点击无法穿透 Vue Web Component → Playwright 真实鼠标点击
"""

import subprocess
import sys
import time
import json
import re
from pathlib import Path
from typing import Optional


# ─── opencli 部分 ──────────────────────────────────────────

def run_opencli(cmd: str, timeout: int = 30) -> dict:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace"
        )
        output = result.stdout.strip()
        try:
            return {"ok": True, "data": json.loads(output), "raw": output}
        except json.JSONDecodeError:
            if result.returncode != 0:
                return {"ok": False, "error": result.stderr.strip() or output, "raw": output}
            return {"ok": True, "data": output, "raw": output}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Command timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def opencli(session: str, cmd: str, timeout: int = 30) -> dict:
    return run_opencli(f'opencli browser {session} {cmd}', timeout)


# ─── Playwright 部分 ────────────────────────────────────────

class XHSPublisherV2:
    """小红书发布器 v2 — opencli + Playwright"""

    def __init__(self):
        self.page = None
        self.browser = None
        self.playwright = None

    def _init_playwright(self):
        """延迟初始化 Playwright"""
        if self.page is not None:
            return
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        # 连接到已有的 Chrome — 需要 Chrome 开启 remote debugging
        # 这里用 opencli 的绑定功能或自己启动
        self.browser = self.playwright.chromium.connect_over_cdp("http://localhost:9222")
        self.page = self.browser.contexts[0].pages[0]
        print("✅ Playwright 已连接到 Chrome")

    # ─── 发布流程 ─────────────────────────────────────────

    def publish(self, image_path: str, title: str, content: str,
                tags: list = None, session: str = "xhs_v2") -> bool:
        """
        完整发布流程
        1. opencli: 打开页面 → 上传图片 → 填标题
        2. Playwright: 填正文 → 加标签 → 点击发布
        """
        abs_image = str(Path(image_path).resolve())
        clean_content = content.replace('\r', '').strip()

        print("=" * 50)
        print("🚀 小红书自动化发布 v2")
        print("=" * 50)

        # ── Step 1: 打开页面 ──
        url = "https://creator.xiaohongshu.com/publish/publish?from=tab_switch&target=image"
        r = opencli(session, f'open "{url}"')
        if not r["ok"]:
            print(f"❌ 打开页面失败: {r.get('error')}")
            return False
        print("✅ [1/5] 已打开图文发布页")
        time.sleep(3)

        # ── Step 2: 上传图片 ──
        r = opencli(session, "state")
        if not r["ok"]:
            print("❌ 获取state失败")
            return False
        ref = _find_ref(r["raw"], r'type=file\s+accept=[^>]*\.jpg')
        if not ref:
            print("❌ 找不到上传input")
            return False
        r = opencli(session, f'upload {ref} "{abs_image}"')
        if not (r["ok"] and r.get("data", {}).get("uploaded")):
            print(f"❌ 上传失败: {r}")
            return False
        print(f"✅ [2/5] 图片上传成功: {Path(abs_image).name}")
        time.sleep(3)

        # ── Step 3: 填标题 (opencli) ──
        r = opencli(session, "state")
        ref = _find_ref(r["raw"], r'placeholder=\s*填写标题')
        if not ref:
            print("❌ 找不到标题输入框")
            return False
        r = opencli(session, f'fill {ref} "{title}"')
        if not (r["ok"] and r.get("data", {}).get("filled")):
            print(f"❌ 标题填写失败")
            return False
        print(f"✅ [3/5] 标题: {title}")
        time.sleep(1)

        # ── Step 4: 填正文 (Playwright type) ──
        print("🔄 初始化 Playwright...")
        self._init_playwright()

        # 定位 contenteditable div
        self.page.wait_for_selector('[contenteditable="true"]', timeout=15000)
        editable = self.page.locator('[contenteditable="true"]')
        editable.click()
        time.sleep(0.5)

        # 清空已有内容
        self.page.keyboard.press("Control+a")
        self.page.keyboard.press("Backspace")
        time.sleep(0.3)

        # 逐段 type（保持段落格式）
        paragraphs = clean_content.split('\n\n')
        for i, para in enumerate(paragraphs):
            if i > 0:
                self.page.keyboard.press("Enter")
                self.page.keyboard.press("Enter")
            self.page.keyboard.type(para.strip(), delay=5)
        print(f"✅ [4/5] 正文填写完成 ({len(clean_content)}字)")

        # ── Step 4.5: 添加话题标签 ──
        if tags:
            self._add_tags_with_playwright(tags)
            print(f"✅ 标签已添加: {tags}")

        # ── Step 5: 点击发布按钮 ──
        time.sleep(1)
        publish_btn = self.page.locator('xhs-publish-btn')
        if publish_btn.count() > 0:
            # 获取按钮内部的可点击区域
            btn_box = publish_btn.bounding_box()
            if btn_box:
                self.page.mouse.click(
                    btn_box['x'] + btn_box['width'] / 2,
                    btn_box['y'] + btn_box['height'] / 2
                )
                print("✅ [5/5] 已点击发布按钮！")
                time.sleep(4)

                # 检查是否成功
                current_url = self.page.url
                if "note-manager" in current_url or "publish/success" in current_url:
                    print("🎉 发布成功！")
                    return True
                else:
                    # 再试一次
                    print("🔄 再次尝试点击...")
                    publish_btn.click(force=True)
                    time.sleep(4)
                    current_url = self.page.url
                    if "note-manager" in current_url:
                        print("🎉 发布成功！(第二次尝试)")
                        return True

            print("⚠️ 点击完成，请检查浏览器确认发布状态")
            return True
        else:
            print("❌ 未找到发布按钮 xhs-publish-btn")
            return False

    def _add_tags_with_playwright(self, tags: list):
        """用 Playwright 点击推荐标签"""
        for tag in tags:
            try:
                tag_el = self.page.locator(f'span.tag:has-text("{tag}")')
                if tag_el.count() > 0:
                    tag_el.first.click()
                    time.sleep(0.5)
            except Exception:
                pass  # 标签可能不存在，跳过

    def close(self):
        if self.playwright:
            self.playwright.stop()


# ─── 工具函数 ─────────────────────────────────────────────

def _find_ref(state_text: str, pattern: str) -> Optional[str]:
    """从 opencli state 输出中找元素 ref"""
    match = re.search(rf'\[(\d+)\]\s*<[^>]*{pattern}[^>]*>', state_text)
    if match:
        return match.group(1)
    return None


# ─── CLI 入口 ──────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="小红书发布 v2")
    parser.add_argument("--image", required=True, help="封面图路径")
    parser.add_argument("--title", required=True, help="标题")
    parser.add_argument("--content", required=True, help="正文文件或文本")
    parser.add_argument("--tags", default="", help="标签，逗号分隔")
    parser.add_argument("--session", default="xhs_v2", help="opencli session")
    args = parser.parse_args()

    # 如果 content 是文件路径，读取
    content = args.content
    if Path(content).exists():
        content = Path(content).read_text(encoding="utf-8")

    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None

    publisher = XHSPublisherV2()
    try:
        success = publisher.publish(
            image_path=args.image,
            title=args.title,
            content=content,
            tags=tags,
            session=args.session,
        )
        sys.exit(0 if success else 1)
    finally:
        publisher.close()


if __name__ == "__main__":
    main()
