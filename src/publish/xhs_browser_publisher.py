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
from pathlib import Path
from typing import Optional


def run(cmd: str, timeout: int = 30) -> dict:
    """运行 opencli 命令并解析 JSON 输出"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace"
        )
        output = result.stdout.strip()
        # 尝试解析 JSON
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


def opencli_browser(session: str, cmd: str, timeout: int = 30) -> dict:
    """执行 opencli browser 命令"""
    full_cmd = f'opencli browser {session} {cmd}'
    return run(full_cmd, timeout)


class XHSBrowserPublisher:
    """小红书浏览器发布器"""

    def __init__(self, session: str = "xhs_publish"):
        self.session = session

    def open_publish_page(self) -> bool:
        """打开图文发布页"""
        url = "https://creator.xiaohongshu.com/publish/publish?from=tab_switch&target=image"
        r = opencli_browser(self.session, f'open "{url}"')
        if r["ok"]:
            print("✅ 已打开图文发布页")
            time.sleep(2)
            return True
        print(f"❌ 打开页面失败: {r.get('error')}")
        return False

    def upload_image(self, image_path: str) -> bool:
        """上传封面图片"""
        abs_path = str(Path(image_path).resolve())
        if not Path(abs_path).exists():
            print(f"❌ 图片不存在: {abs_path}")
            return False

        # 先获取 state 找 file input ref
        r = opencli_browser(self.session, "state")
        if not r["ok"]:
            print(f"❌ 获取state失败: {r.get('error')}")
            return False

        # 从 state 中找 file input 的 ref
        ref = self._find_file_input_ref(r["raw"])
        if not ref:
            print("❌ 找不到文件上传input")
            return False

        # 上传
        r2 = opencli_browser(self.session, f'upload {ref} "{abs_path}"')
        if r2["ok"] and r2.get("data", {}).get("uploaded"):
            print(f"✅ 图片上传成功: {Path(abs_path).name}")
            time.sleep(2)
            return True
        print(f"❌ 上传失败: {r2.get('error') or r2}")
        return False

    def fill_title(self, title: str) -> bool:
        """填写标题 - 用 eval 定位 input"""
        r = opencli_browser(self.session, 'fill --name "填写标题会有更多赞哦" "' + title + '"')
        if r["ok"] and isinstance(r.get("data"), dict) and r["data"].get("filled"):
            print(f"✅ 标题填写成功: {title}")
            return True

        # fallback: 用 state 找 ref
        r = opencli_browser(self.session, "state")
        if r["ok"]:
            ref = self._find_element_ref(r["raw"], 'placeholder=')
            if ref:
                r2 = opencli_browser(self.session, f'fill {ref} "{title}"')
                if r2["ok"] and r2.get("data", {}).get("filled"):
                    print(f"✅ 标题填写成功: {title}")
                    return True
        print(f"❌ 标题填写失败")
        return False

    def fill_content(self, content: str) -> bool:
        """填写正文 - 用 fill 命令填充 contenteditable"""
        clean = content.replace('"', "'").replace("\r", "")

        r = opencli_browser(self.session, "state")
        if r["ok"]:
            ref = self._find_element_ref(r["raw"], 'contenteditable=true')
            if ref:
                r2 = opencli_browser(self.session, f'fill {ref} "{clean}"', timeout=30)
                if r2["ok"]:
                    print("✅ 正文填写成功")
                    return True
        print(f"❌ 正文填写失败")
        return False

    def add_tags(self, tags: list) -> bool:
        """添加话题标签"""
        for tag in tags:
            r = opencli_browser(self.session, "state")
            if not r["ok"]:
                continue

            # 找包含此 tag 文本的 span
            ref = self._find_element_ref(r["raw"], f'>{tag}<')
            if not ref:
                print(f"⚠️ 标签 '{tag}' 未找到，跳过")
                continue

            r2 = opencli_browser(self.session, f"click {ref}")
            if r2["ok"]:
                print(f"✅ 标签添加成功: {tag}")
                time.sleep(1)
            else:
                print(f"⚠️ 标签点击失败: {tag}")

        return True

    def publish(self) -> bool:
        """触发发布 — 调用 xhs-publish-btn 暴露的 _onPublish 函数"""
        print("🔄 尝试发布...")

        # ✅ 已验证：xhs-publish-btn 暴露 _onPublish 函数，直接调用即可触发 Vue 发布逻辑
        js = "var b=document.querySelector('xhs-publish-btn'); if(b && typeof b._onPublish==='function'){b._onPublish();'published'}else{'fail'}"
        r = opencli_browser(self.session, f"eval '{js}'")
        print(f"  发布结果: {r.get('data') or r.get('raw','')}")
        time.sleep(4)

        # 检查是否发布成功
        check = opencli_browser(self.session, "eval 'window.location.href'")
        url = check.get("raw", "")
        if "published=true" in url:
            print("🎉 全自动发布成功！")
            return True

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
        if self.publish():
            print("\n🎉 发布流程完成！")
            return True

        print("\n⚠️ 发布流程执行完毕，请手动确认发布结果")
        return True

    @staticmethod
    def _find_file_input_ref(state_text: str) -> Optional[str]:
        """从 opencli state 输出中找到 file input 的 ref"""
        match = re.search(r'\[(\d+)\]\s*<input\s+type=file\s+accept=[^>]*\.jpg', state_text)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _find_element_ref(state_text: str, pattern: str) -> Optional[str]:
        """从 opencli state 输出中匹配元素 ref"""
        match = re.search(rf'\[(\d+)\]\s*<[^>]*{pattern}[^>]*>', state_text)
        if match:
            return match.group(1)
        return None


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
