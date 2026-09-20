import os

from update_html import generate_html


def test_generate_html_works_for_completed_trades(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with open("completed_trades.csv", "w", encoding="utf-8") as f:
        f.write("Symbol,Status\nABC,Win\nXYZ,Loss\n")

    generate_html()

    assert os.path.exists("index.html")
    html = open("index.html", "r", encoding="utf-8").read()
    assert "AI Trading Portfolio" in html
    assert "table" in html
