#!/usr/bin/env python3
"""Minify app.js -> bookmarklet.txt, and generate install.html (drag-to-install).

    python3 build.py
"""
import re

src = open("app.js").read()
src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)       # /* block */ comments
src = re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)    # own-line // comments
mini = re.sub(r"\s+", " ", src).strip()                    # collapse whitespace
assert "//" not in mini.replace("https://", ""), "stray // comment in minified output"

bookmarklet = "javascript:" + mini
open("bookmarklet.txt", "w").write(bookmarklet + "\n")
print(f"wrote bookmarklet.txt ({len(bookmarklet)} chars)")

# install.html — open it, drag the button to the bookmarks bar. Works on any Mac, no Terminal.
href = bookmarklet.replace("&", "&amp;").replace('"', "&quot;")
html = """<!doctype html><html><head><meta charset="utf-8"><title>NYC Tennis — setup</title>
<style>
 body{margin:0;font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
   background:#f4f6f5;color:#16181d;display:flex;justify-content:center;padding:48px 16px}
 .card{background:#fff;max-width:540px;width:100%;border-radius:18px;box-shadow:0 10px 40px rgba(0,0,0,.10);padding:34px 36px}
 h1{margin:0 0 4px;font-size:24px}.sub{color:#6b7280;margin:0 0 26px}
 .drag{display:inline-flex;align-items:center;gap:8px;background:#1a7d4b;color:#fff;text-decoration:none;
   font-weight:700;font-size:17px;padding:13px 22px;border-radius:11px;box-shadow:0 4px 14px rgba(26,125,75,.35);cursor:grab}
 .dragwrap{text-align:center;margin:8px 0 6px}.hint{text-align:center;color:#9aa0a8;font-size:13px;margin-bottom:26px}
 ol{padding-left:22px;margin:0}li{margin:9px 0}
 code{background:#eef0f2;border-radius:5px;padding:1px 6px;font-size:14px}
 .note{margin-top:22px;padding:13px 15px;background:#e7f5ec;border-radius:10px;font-size:14px;color:#136b3e}
</style></head><body><div class="card">
 <h1>🎾 NYC Tennis — 1-minute setup</h1>
 <p class="sub">Find open Manhattan courts &amp; auto-fill your reservation, right in your browser.</p>
 <div class="dragwrap"><a class="drag" href="__HREF__">🎾 Tennis</a></div>
 <p class="hint">↑ drag this button up to your bookmarks bar</p>
 <ol>
   <li>Press <code>⌘⇧B</code> to show Chrome's bookmarks bar.</li>
   <li><b>Drag</b> the green <b>🎾 Tennis</b> button up onto that bar.</li>
   <li>Go to <code>nycgovparks.org/tennisreservation</code> and click the <b>Tennis</b> bookmark.</li>
   <li>Click <b>⚙</b> in the panel once to enter your own permit number &amp; details (saved only on your Mac).</li>
 </ol>
 <div class="note">Your details never leave your computer — they're stored only in this browser and used to
 auto-fill the reservation form. It never submits or pays; you always review and pay yourself.</div>
</div></body></html>
""".replace("__HREF__", href)
open("install.html", "w").write(html)
print(f"wrote install.html ({len(html)} chars)")
