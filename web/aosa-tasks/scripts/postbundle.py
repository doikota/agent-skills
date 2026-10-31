"""bundle.html の後処理: <title> とビューポート meta を先頭へ移し、Google Fonts の読み込みを差し込む。

html-inline は外部 <link> を inline しようとして失敗するため、フォントはバンドル後に入れる。
"""
import re
import sys
from pathlib import Path

FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700;900'
         '&family=Noto+Sans+JP:wght@400;500;700&family=IBM+Plex+Mono:wght@500&display=swap">')

path = Path(sys.argv[1] if len(sys.argv) > 1 else "bundle.html")
s = path.read_text(encoding="utf-8")
title = re.search(r"<title>.*?</title>", s).group(0)
s = s.replace(title, "", 1)
s = re.sub(r'<meta name="?claude:viewport-fit-sides"? content="?cover"?>', "", s, count=1)
s = re.sub(r"(<html[^>]*>)", lambda m: m.group(1) + title + '<meta name="claude:viewport-fit-sides" content="cover">' + FONTS, s, count=1)
path.write_text(s, encoding="utf-8")
print(f"post-processed {path}")
