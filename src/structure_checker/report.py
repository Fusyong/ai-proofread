import html
import json
from typing import List

from .models import Diagnostic, Node


def render_json(roots: List[Node], diagnostics: List[Diagnostic], out_json: str):
    def node_to_obj(n: Node):
        return {
            "rule": n.rule_id,
            "level": n.level,
            "start": n.token.start,
            "end": n.token.end,
            "text": n.token.raw_text,
            "number": n.token.number_value,
            "children": [node_to_obj(c) for c in n.children],
        }

    obj = {
        "roots": [node_to_obj(r) for r in roots],
        "diagnostics": [
            {
                "kind": d.kind,
                "message": d.message,
                "start": d.position[0],
                "end": d.position[1],
                "extra": d.extra,
            }
            for d in diagnostics
        ],
    }
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def render_html(text: str, roots: List[Node], diagnostics: List[Diagnostic], out_html: str):
    def esc(s: str) -> str:
        return html.escape(s, quote=False)

    def node_li(n: Node) -> str:
        label = f"[{n.rule_id}] {esc(n.token.raw_text)}"
        anchor = f"pos-{n.token.start}"
        inner = "".join(node_li(c) for c in n.children)
        return f"<li><a href=\"#{anchor}\">{label}</a>{('<ul>'+inner+'</ul>') if inner else ''}</li>"

    # 标记原文中的锚点
    anchors = sorted({(n.token.start, n.token.end) for root in roots for n in walk(root)})
    html_text = []
    last = 0
    for s, e in sorted([p for p in anchors], key=lambda x: x[0]):
        if s > last:
            html_text.append(esc(text[last:s]))
        html_text.append(f"<span id=\"pos-{s}\" class=\"hit\">{esc(text[s:e])}</span>")
        last = e
    html_text.append(esc(text[last:]))

    diag_html = "".join(
        f"<li><b>{esc(d.kind)}</b> @[{d.position[0]},{d.position[1]}]: {esc(d.message)}</li>"
        for d in diagnostics
    )

    tree_html = "".join(node_li(r) for r in roots)

    doc = f"""
<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <title>结构检查报告</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans SC', 'Microsoft Yahei', sans-serif; display: grid; grid-template-columns: 360px 1fr; height: 100vh; margin: 0; }}
    aside {{ overflow: auto; border-right: 1px solid #ddd; padding: 12px; }}
    main {{ overflow: auto; padding: 16px; }}
    .hit {{ background: #fff7cc; border-bottom: 1px solid #f0d000; }}
    .panel {{ margin-bottom: 16px; }}
    .panel h2 {{ margin: 8px 0; font-size: 16px; }}
    ul {{ margin: 4px 0 8px 20px; }}
    a {{ text-decoration: none; color: #0366d6; }}
  </style>
  <script>
  window.addEventListener('click', (e) => {{
    if (e.target.tagName === 'A' && e.target.getAttribute('href')?.startsWith('#pos-')) {{
      const id = e.target.getAttribute('href').slice(1);
      const el = document.getElementById(id);
      if (el) {{ el.scrollIntoView({{ behavior: 'smooth', block: 'center' }}); }}
    }}
  }});
  </script>
  </head>
  <body>
    <aside>
      <div class=\"panel\">
        <h2>结构树</h2>
        <ul>{tree_html}</ul>
      </div>
      <div class=\"panel\">
        <h2>诊断</h2>
        <ul>{diag_html}</ul>
      </div>
    </aside>
    <main>
      <div class=\"panel\">
        <h2>原文（命中高亮）</h2>
        <div>{''.join(html_text)}</div>
      </div>
    </main>
  </body>
  </html>
    """

    with open(out_html, "w", encoding="utf-8") as f:
        f.write(doc)


def walk(root: Node):
    yield root
    for c in root.children:
        yield from walk(c)



