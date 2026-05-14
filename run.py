import feedparser
import re
from datetime import datetime, timezone, timedelta

# arXiv RSS（cond-mat, recent）
FEED_URL = "https://arxiv.org/rss/cond-mat/"  # recentはフィード側で近いものが出るので日付で絞ります

# 週1対象：過去7日
NOW = datetime.now(timezone.utc)
SINCE = NOW - timedelta(days=7)

# ここを調整：キーワード（英語推奨）
KEYWORDS = [
    r"\bRashba\b",
    r"\b(two[- ]dimensional|2D)\b",
    r"\b(two[- ]dimensional material|2D material)\b",
    r"\bsurface\b",
    r"\bsuperstructure\b",
    r"\bsurface reconstruction\b",
    r"\b(topological surface)\b",
]

CATEGORY_HINTS = [
    # cond-mat内の想定カテゴリをキーワードで当てに行く（必要なら増減）
    r"surface",
    r"rashes",  # 誤爆防止に弱いので基本は不要。必要なら削除。
]

def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def pubdate_to_dt(entry):
    # feedparserがよく返す形式に合わせる
    if entry.get("published_parsed"):
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if entry.get("updated_parsed"):
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    return None

def score(entry):
    text = (entry.get("title","") + " " + entry.get("summary","")).lower()
    s = 0
    for pat in KEYWORDS:
        if re.search(pat, entry.get("title",""), flags=re.IGNORECASE):
            s += 5
        if re.search(pat, entry.get("summary",""), flags=re.IGNORECASE):
            s += 2
        if re.search(pat, text, flags=re.IGNORECASE):
            s += 1
    return s

def make_item_html(entry):
    title = normalize_text(entry.get("title"))
    summary = normalize_text(entry.get("summary"))
    link = entry.get("link")
    published = entry.get("published", "") or entry.get("updated", "")
    # arXivはsummaryが長いので少し切る
    summary_short = summary[:400] + ("..." if len(summary) > 400 else "")
    return f"""
    <div class="card">
      <div class="meta">{published}</div>
      <div class="title"><a href="{link}" target="_blank" rel="noopener">{title}</a></div>
      <div class="abs">{summary_short}</div>
    </div>
    """

def main():
    feed = feedparser.parse(FEED_URL)

    matches = []
    for entry in feed.entries:
        dt = pubdate_to_dt(entry)
        if not dt:
            continue
        if not (SINCE <= dt <= NOW):
            continue

        sc = score(entry)
        if sc <= 0:
            continue

        matches.append((sc, dt, entry))

    matches.sort(key=lambda x: (x[0], x[1]), reverse=True)

    # 出力：docs/index.html を生成
    os.makedirs("docs", exist_ok=True)

    cards = "\n".join(make_item_html(e) for (_, _, e) in matches) or "<p>該当なし（キーワード調整してください）</p>"

    html = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>arXiv cond-mat Weekly (Rashba/2D/Surface)</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 28px; color:#111; }}
    .header {{ margin-bottom: 18px; }}
    .card {{ border:1px solid #ddd; border-radius:12px; padding:14px 16px; margin:12px 0; background:#fff; }}
    .meta {{ color:#666; font-size: 12px; margin-bottom: 8px; }}
    .title a {{ color:#0b57d0; font-weight:700; text-decoration:none; }}
    .title a:hover {{ text-decoration:underline; }}
    .abs {{ color:#333; margin-top: 10px; line-height: 1.5; }}
    .footer {{ margin-top: 22px; color:#666; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>arXiv cond-mat 最新 7日</h1>
    <p>フィルタ: Rashba / 2D / surface / superstructure / surface reconstruction（スコア順）</p>
  </div>

  {cards}

  <div class="footer">
    Generated automatically by run.py
  </div>
</body>
</html>"""

    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    import os
    main()
