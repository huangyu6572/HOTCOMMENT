"""
小红书一键发布 v2 — 纯 opencli 方案（已验证全自动发布）

关键突破：
1. 正文用 eval innerHTML 赋值（解决 fill contenteditable 截断问题）
2. 发布按钮：xhs-publish-btn 是 Vue Web Component，click/dispatchEvent 均无效
   但元素上暴露了 _onPublish 函数，直接 eval 调用即可触发 Vue 内部发布逻辑
   验证标志：发布后 URL 出现 published=true 参数
"""

import subprocess
import sys
import time
import json
import re
import argparse
from pathlib import Path
from typing import Optional


def oc(session: str, cmd: str, timeout: int = 30) -> dict:
    """运行 opencli browser 命令"""
    full = f'opencli browser {session} {cmd}'
    try:
        r = subprocess.run(full, shell=True, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        out = r.stdout.strip()
        try:
            return {"ok": True, "data": json.loads(out), "raw": out}
        except json.JSONDecodeError:
            return {"ok": r.returncode == 0, "error": r.stderr.strip() or out, "raw": out}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def find_ref(state: str, pattern: str) -> Optional[str]:
    m = re.search(rf'\[(\d+)\]\s*<[^>]*{pattern}[^>]*>', state)
    return m.group(1) if m else None


def publish(image_path: str, title: str, content: str,
            tags: list = None, session: str = "xhs_v2") -> bool:
    """完整发布流程"""

    image = str(Path(image_path).resolve())
    if not Path(image).exists():
        print(f"❌ 图片不存在: {image}")
        return False

    print("=" * 50)
    print("🚀 小红书发布 v2")
    print("=" * 50)

    # ── 1. 打开页面 ──
    url = "https://creator.xiaohongshu.com/publish/publish?from=tab_switch&target=image"
    r = oc(session, f'open "{url}"')
    if not r["ok"]:
        print(f"❌ 打开失败: {r.get('error')}")
        return False
    print("✅ [1/5] 打开图文发布页")
    time.sleep(3)

    # ── 2. 上传图片 ──
    r = oc(session, "state")
    ref = find_ref(r["raw"], r'type=file\s+accept=[^>]*\.jpg')
    if not ref:
        print("❌ 找不到上传input")
        return False
    r = oc(session, f'upload {ref} "{image}"')
    if not (r["ok"] and isinstance(r.get("data"), dict) and r["data"].get("uploaded")):
        print(f"❌ 上传失败")
        return False
    print("✅ [2/5] 图片上传成功")
    time.sleep(3)

    # ── 3. 填标题 ──
    r = oc(session, "state")
    ref = find_ref(r["raw"], r'placeholder=\s*填写标题')
    if not ref:
        print("❌ 找不到标题框")
        return False
    r = oc(session, f'fill {ref} "{title}"')
    if not r["ok"]:
        print("❌ 标题填写失败")
        return False
    print(f"✅ [3/5] 标题: {title}")

    # ── 4. 填正文 (eval innerHTML) ──
    # 把正文转成 HTML 段落
    paras = content.strip().split('\n\n')
    html_parts = []
    for p in paras:
        p_clean = p.strip().replace("'", "\\'").replace('"', '&quot;').replace('\n', '<br>')
        if p_clean:
            html_parts.append(f'<p>{p_clean}</p>')
    html = ''.join(html_parts)

    # 用 eval 直接设置 innerHTML（绕过 fill 的截断问题）
    js = f"var d=document.querySelector('[contenteditable=true]'); if(d){{ d.innerHTML='{html}'; d.dispatchEvent(new Event('input',{{bubbles:true}})); 'ok '+d.innerText.length }}else{{ 'not found' }}"
    r = oc(session, f'eval "{js}"', timeout=15)
    raw = r.get("raw", "")
    print(f"✅ [4/5] 正文: {raw}")

    time.sleep(1)

    # ── 5. 加标签 ──
    if tags:
        r = oc(session, "state")
        for tag in tags:
            ref = find_ref(r["raw"], f'>{tag}<')
            if ref:
                oc(session, f"click {ref}")
                time.sleep(0.5)
        print(f"✅ 标签已尝试添加")

    # ── 6. 发布！──
    # 策略：xhs-publish-btn 是 Vue Web Component，click/dispatchEvent 均无效
    # 但元素暴露了 _onPublish 函数 → 直接调用触发 Vue 发布逻辑
    r = oc(session, "eval 'var b=document.querySelector(\"xhs-publish-btn\"); b?b.getAttribute(\"submit-disabled\"):\"not found\"'")
    print(f"🔍 发布按钮状态: {r.get('raw','')}")

    js_publish = "var b=document.querySelector('xhs-publish-btn'); if(b&&typeof b._onPublish==='function'){b._onPublish();'published'}else{'fail: _onPublish not found'}"
    r = oc(session, f'eval "{js_publish}"')
    print(f"🖱️  调用 _onPublish: {r.get('raw','')}")

    time.sleep(5)

    # 检查结果：发布成功 URL 带 published=true
    r = oc(session, "eval 'window.location.href'")
    url = r.get("raw", "")
    if "published=true" in url:
        print("🎉 全自动发布成功！（published=true）")
        return True

    print(f"📍 当前URL: {url}")
    print("⚠️  未检测到 published=true，请手动检查")
    return False


def main():
    parser = argparse.ArgumentParser(description="小红书发布 v2")
    parser.add_argument("--image", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--tags", default="")
    parser.add_argument("--session", default="xhs_v2")
    args = parser.parse_args()

    content = args.content
    if Path(content).exists():
        content = Path(content).read_text(encoding="utf-8")

    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    success = publish(
        image_path=args.image,
        title=args.title,
        content=content,
        tags=tags,
        session=args.session,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
