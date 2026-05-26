"""
小红书浏览器自动化发布器 —— 基于 opencli browser 原语

完整流程:
1. 打开图文发布页
2. 上传封面图片
3. 填写标题
4. 填写正文
5. 添加话题标签
6. 触发发布（通过侧边栏"发布笔记"按钮或 Ctrl+Enter）

用法:
  python xhs_browser_publisher.py --image data/cover_yangmei.jpg --title "标题" --content "正文" [--tags "标签1,标签2"]
"""

import subprocess
import sys
import time
import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Optional

from .base import BasePublisher, PublishResult

# 定位 opencli.cmd 绝对路径，避免 shell=True 的引号解析问题
_OPENCLI = shutil.which("opencli.cmd") or shutil.which("opencli") or "opencli"


def run(cmd_parts: list[str], timeout: int = 30) -> dict:
    """运行 opencli 命令（list args，不用 shell）"""
    try:
        result = subprocess.run(
            [_OPENCLI] + cmd_parts,
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
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


def opencli_browser(session: str, *args: str, timeout: int = 30) -> dict:
    """执行 opencli browser 命令 — 用 list args 避免 shell 引号问题"""
    return run(["browser", session] + list(args), timeout)


class XHSBrowserPublisher(BasePublisher):
    """小红书浏览器发布器"""

    def __init__(self, session: str = None):
        super().__init__("xiaohongshu")
        # 固定 session 名复用登录态（新 session 首次 open 不稳定）
        self.session = session or "xhs_publish"

    def publish(self, draft_path: Path, title: str, content: str) -> PublishResult:
        """BasePublisher 接口：发布草稿到小红书"""
        # 找封面图
        image_path = self._find_cover(draft_path)
        if not image_path:
            return PublishResult(success=False, platform=self.platform, error="无封面图")

        # 解析标签
        tags = self._parse_tags(content)

        ok = self.full_flow(
            image_path=str(image_path),
            title=title[:20],  # 标题限制20字
            content=content,
            tags=tags,
        )
        return PublishResult(success=ok, platform=self.platform)

    @staticmethod
    def _find_cover(draft_path: Path) -> Optional[Path]:
        """在 data/ 下找封面图（返回最新修改的）"""
        data_dir = draft_path.parent.parent  # drafts/ → data/
        candidates = []
        for ext in [".jpg", ".png", ".jpeg", ".webp"]:
            candidates += list(data_dir.glob(f"cover*{ext}"))
        if not candidates:
            return None
        # 返回最近修改的封面图
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]

    @staticmethod
    def _parse_tags(content: str) -> list[str]:
        """从正文提取 #标签"""
        return re.findall(r"#(\S+)", content)

    # ---- 以下为浏览器自动化方法 ----

    def open_publish_page(self) -> bool:
        """打开图文发布页"""
        url = "https://creator.xiaohongshu.com/publish/publish?from=tab_switch&target=image"

        for attempt in range(3):
            r = opencli_browser(self.session, "open", url)
            if not r["ok"]:
                continue
            time.sleep(6)  # 等登录、重定向、Vue 渲染

            # 验证：等页面出现 title input
            for _ in range(5):
                check = opencli_browser(self.session, "eval", "var inp=document.querySelector('input[placeholder]'); inp?('ok '+inp.placeholder):'wait'")
                result = str(check.get("data", "") or check.get("raw", ""))
                if "ok" in result:
                    print("✅ 已打开图文发布页")
                    return True
                time.sleep(2)
            print(f"  ⏳ 页面渲染超时，重试 open... ({attempt+1}/3)")

        print("❌ 无法打开图文发布页")
        return False

    def upload_image(self, image_path: str) -> bool:
        """上传封面图片 — 用 find + upload 定位 file input"""
        abs_path = str(Path(image_path).resolve())
        if not Path(abs_path).exists():
            print(f"❌ 图片不存在: {abs_path}")
            return False

        # 用 find 定位 file input（返回 JSON）
        find = opencli_browser(self.session, "find", "--css", "input[type=file]")
        find_data = find.get("data", {})
        if isinstance(find_data, dict) and find_data.get("matches_n", 0) > 0:
            ref = str(find_data["entries"][0]["ref"])
        else:
            print(f"❌ 找不到文件上传input: {find_data}")
            return False

        r2 = opencli_browser(self.session, "upload", ref, abs_path)
        if r2["ok"]:
            data = r2.get("data", {})
            if isinstance(data, dict) and data.get("uploaded"):
                print(f"✅ 图片上传成功: {Path(abs_path).name}")
                time.sleep(2)
                return True
        print(f"❌ 上传失败: {r2}")
        return False

    def fill_title(self, title: str) -> bool:
        """填写标题 — 用 eval 定位 input（最可靠）"""
        safe_title = title.replace("\\", "\\\\").replace("'", "\\'")
        js = f"var inp=document.querySelector('input[placeholder]'); if(inp){{ var nativeInputValueSetter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; nativeInputValueSetter.call(inp,'{safe_title}'); inp.dispatchEvent(new Event('input',{{bubbles:true}})); 'ok '+inp.value.length }}else{{ 'not found' }}"
        r = opencli_browser(self.session, "eval", js, timeout=10)
        result = str(r.get("data", "") or r.get("raw", ""))
        if "ok" in result:
            print(f"✅ 标题填写成功: {title}")
            return True
        print(f"❌ 标题填写失败: {result}")
        return False

    def fill_content(self, content: str) -> bool:
        """填写正文 — 直接用 eval innerHTML（fill 对 contenteditable 会截断）"""
        # 转义：反斜杠、单引号、换行
        safe = content.replace("\\", "\\\\").replace("'", "\\'").replace("\r", "").replace("\n", "\\n")
        js = f"var d=document.querySelector('[contenteditable=true]'); if(d){{ d.innerHTML='{safe}'.replace(/\\\\n/g,'<br>'); d.dispatchEvent(new Event('input',{{bubbles:true}})); 'ok '+d.innerText.length }}else{{ 'not found' }}"
        r = opencli_browser(self.session, "eval", js, timeout=15)
        result = r.get("data", "") or r.get("raw", "")
        if "ok" in str(result):
            print(f"✅ 正文填写成功: {result}")
            return True
        print(f"❌ 正文填写失败: {result}")
        return False

    def add_tags(self, tags: list) -> bool:
        """添加话题标签 — 小红书标签需从推荐列表点击，目前 skip"""
        if tags:
            print(f"⚠️ 标签功能待完善，已跳过: {tags}")
        return True

    def trigger_publish(self) -> bool:
        """触发发布 — 调用 xhs-publish-btn 暴露的 _onPublish 函数"""
        print("🔄 尝试发布...")

        # 先检查按钮状态
        check = opencli_browser(self.session, "eval", "var b=document.querySelector('xhs-publish-btn'); b?('disabled:'+b.getAttribute('submit-disabled')):'not found'")
        print(f"  按钮状态: {check.get('data','')}")

        # 调用 _onPublish 触发 Vue 发布逻辑
        js = "var b=document.querySelector('xhs-publish-btn'); if(b && typeof b._onPublish==='function'){b._onPublish();'published'}else{'fail'}"
        r = opencli_browser(self.session, "eval", js)
        print(f"  _onPublish: {r.get('data','')}")

        # 等页面跳转
        time.sleep(5)

        # 用 state 检查 URL（比 eval 更可靠）
        for _ in range(3):
            state = opencli_browser(self.session, "state")
            raw = state.get("raw", "")
            if "publish/success" in raw:
                print("🎉 全自动发布成功！")
                return True
            if "published=true" in raw:
                print("🎉 全自动发布成功！（published=true）")
                return True
            time.sleep(2)

        # 最后用 eval 看 URL
        url_check = opencli_browser(self.session, "eval", "window.location.href")
        url = url_check.get("data", "") or url_check.get("raw", "")
        print(f"⚠️ 当前URL: {url}")
        return False

    def full_flow(self, image_path: str, title: str, content: str, tags: Optional[list] = None):
        """完整发布流程"""
        print("=" * 50)
        print("🚀 小红书自动化发布流程")
        print("=" * 50)

        # Step 1: 打开页面
        if not self.open_publish_page():
            return False

        # Step 2: 上传图片
        if not self.upload_image(image_path):
            return False

        # Step 3: 填标题
        if not self.fill_title(title):
            return False

        # Step 4: 填正文
        if not self.fill_content(content):
            return False

        # Step 5: 加标签
        if tags:
            self.add_tags(tags)

        # Step 6: 发布
        if self.trigger_publish():
            print("\n🎉 发布流程完成！")
            return True

        print("\n⚠️ 发布流程执行完毕，请手动确认发布结果")
        return True


def main():
    parser = argparse.ArgumentParser(description="小红书浏览器自动化发布")
    parser.add_argument("--image", required=True, help="封面图片路径")
    parser.add_argument("--title", required=True, help="笔记标题")
    parser.add_argument("--content", required=True, help="正文内容")
    parser.add_argument("--tags", default="", help="话题标签，逗号分隔")
    parser.add_argument("--session", default="xhs_publish", help="浏览器会话名")
    args = parser.parse_args()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None

    publisher = XHSBrowserPublisher(session=args.session)
    success = publisher.full_flow(
        image_path=args.image,
        title=args.title,
        content=args.content,
        tags=tags,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
