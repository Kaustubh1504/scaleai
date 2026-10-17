"""Render articles/*.md to medium-html/*.html, each with a 'Copy for Medium' button (copies rich text).

Run from this folder: python3 build_html.py
"""
import html
from pathlib import Path

import markdown

SRC, OUT = Path("articles"), Path("medium-html")

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ max-width: 760px; margin: 0 auto; padding: 24px 16px 80px; font: 18px/1.6 Georgia, serif; color: #222; background: #fff; }}
  .bar {{ position: sticky; top: 0; background: #fff; padding: 12px 0; border-bottom: 1px solid #ddd; margin-bottom: 24px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
  button {{ font: 600 15px system-ui, sans-serif; padding: 10px 18px; border: 0; border-radius: 20px; background: #1a8917; color: #fff; cursor: pointer; }}
  .hint {{ font: 14px system-ui, sans-serif; color: #666; }}
  a.back {{ font: 14px system-ui, sans-serif; color: #1a8917; }}
  pre {{ background: #f2f2f2; padding: 14px; overflow-x: auto; font-size: 14px; line-height: 1.45; }}
  code {{ font-family: Menlo, Consolas, monospace; font-size: 0.85em; background: #f2f2f2; padding: 1px 4px; }}
  pre code {{ background: none; padding: 0; font-size: inherit; }}
  blockquote {{ border-left: 3px solid #222; margin-left: 0; padding-left: 16px; font-style: italic; }}
</style></head>
<body>
<div class="bar">
  {back}
  {button}
  <span class="hint" id="hint">{hint}</span>
</div>
<article id="article">
{body}
</article>
<script>
const btn = document.getElementById("copy");
if (btn) btn.addEventListener("click", () => {{
  const range = document.createRange();
  range.selectNodeContents(document.getElementById("article"));
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
  let ok = false;
  try {{ ok = document.execCommand("copy"); }} catch (e) {{}}
  sel.removeAllRanges();
  document.getElementById("hint").textContent = ok
    ? "Copied. Paste into a new Medium story with Cmd+V."
    : "Copy was blocked. Select the article text and press Cmd+C.";
}});
</script>
</body></html>
"""


def main():
    OUT.mkdir(exist_ok=True)
    links = []
    for md_path in sorted(SRC.glob("*.md")):
        text = md_path.read_text()
        title = text.splitlines()[0].lstrip("# ").strip()
        name = md_path.stem + ".html"
        (OUT / name).write_text(PAGE.format(
            title=html.escape(title), body=markdown.markdown(text, extensions=["fenced_code"]),
            back='<a class="back" href="index.html">&larr; All articles</a>',
            button='<button id="copy">Copy for Medium</button>',
            hint="Click, then paste into a new Medium story (Cmd+V)."))
        links.append(f'<li><a href="{name}">{html.escape(title)}</a></li>')
    index = ("<h1>Medium articles</h1><p>Open an article, click <b>Copy for Medium</b>, "
             "and paste into a new story.</p><ol>" + "".join(links) + "</ol>")
    (OUT / "index.html").write_text(PAGE.format(title="Medium articles", body=index,
                                                back="", button="", hint=""))
    print(f"{len(links)} articles -> {OUT}/")


if __name__ == "__main__":
    main()
