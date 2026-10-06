"""Buat halaman web sinyal harian ke folder docs/ (butuh mtp_bot.py di folder yang sama)."""
import os, html, datetime as dt
from mtp_bot import build

OUT = "docs"
os.makedirs(OUT, exist_ok=True)

TPL = """<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MTP Daily Signal</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--tx:#1a1a1a;--mut:#667;--ac:#0a7d4f}
@media(prefers-color-scheme:dark){:root{--bg:#111;--card:#1c1c1e;--tx:#eee;--mut:#99a;--ac:#3ddc97}}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.5 system-ui,sans-serif}
main{max-width:640px;margin:auto;padding:16px}
h1{font-size:20px;margin:8px 0}.mut{color:var(--mut);font-size:13px}
.card{background:var(--card);border-radius:12px;padding:14px;margin:12px 0;white-space:pre-wrap;font-family:ui-monospace,monospace;font-size:13px}
.card b{color:var(--ac);font-size:15px}
a{color:var(--ac)}
</style></head><body><main>
<h1>MTP Daily Signal</h1>
<div class="mut">Diperbarui: {updated} WIB · Bukan saran investasi</div>
{cards}
<h3>Arsip</h3><div>{archive}</div>
</main></body></html>"""

text = build()
parts = text.split("\n\n")
head, cards = [], []
for p in parts:
    p = p.strip("\n")
    if not p or set(p.replace("\n", "")) <= {"="}: continue
    if p[:2].rstrip(".").isdigit():
        first, _, rest = p.partition("\n")
        cards.append(f'<div class="card"><b>{html.escape(first)}</b>\n{html.escape(rest)}</div>')
    elif p.startswith("🤖") and cards:  # gabung rekomendasi ke kartu sebelumnya
        cards[-1] = cards[-1][:-6] + "\n\n" + html.escape(p) + "</div>"
    else:
        head.append(html.escape(p))

today = dt.date.today().isoformat()
body = f'<div class="card">{"<br>".join(head)}</div>' + "".join(cards)
now = (dt.datetime.utcnow() + dt.timedelta(hours=7)).strftime("%d-%m-%Y %H:%M")

# simpan arsip harian
page = lambda arch: TPL.format(updated=now, cards=body, archive=arch)
open(f"{OUT}/{today}.html", "w", encoding="utf-8").write(page(""))
days = sorted((x[:-5] for x in os.listdir(OUT) if x[:4].isdigit()), reverse=True)[:30]
arch = " · ".join(f'<a href="{d}.html">{d}</a>' for d in days)
open(f"{OUT}/index.html", "w", encoding="utf-8").write(page(arch))
print("OK", len(cards), "kandidat")
