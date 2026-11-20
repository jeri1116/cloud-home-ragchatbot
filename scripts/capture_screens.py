"""보고서용 실행 확인 화면을 캡처한다 (시스템 Chrome + Playwright).

사용: .venv/bin/python scripts/capture_screens.py <CloudFront URL> <GitHub URL>
"""

import html
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVID = ROOT / "docs" / "evidence"
OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

TERM = """<!doctype html><meta charset="utf-8"><style>
body{{margin:0;background:#1e1f29;font:13px/1.55 Menlo,'D2Coding','Apple SD Gothic Neo',monospace;color:#e6e6e6}}
.bar{{background:#2c2e3b;padding:8px 14px;color:#aab;font:12px -apple-system,sans-serif}}
.bar b{{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px}}
pre{{margin:0;padding:14px 18px;white-space:pre-wrap;word-break:break-all}}
.c{{color:#7ee787}} .h{{color:#79c0ff}}
</style><div class="bar"><b style="background:#ff5f57"></b><b style="background:#febc2e"></b><b style="background:#28c840"></b>&nbsp; {title}</div><pre>{body}</pre>"""


def term_html(title: str, text: str) -> str:
    lines = []
    for line in html.escape(text).splitlines():
        if line.startswith("$ ") or line.startswith("## "):
            line = f'<span class="c">{line}</span>'
        elif "HTTP 200" in line or "OK" == line.strip() or "lint OK" in line:
            line = f'<span class="h">{line}</span>'
        lines.append(line)
    return TERM.format(title=html.escape(title), body="\n".join(lines))


def main(site: str, repo: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=2)

        # 1) 배포된 테스트 페이지 + 질문 전송 결과
        page.goto(site, wait_until="networkidle")
        page.wait_for_selector(".dot.ok", timeout=15000)
        page.select_option("#stage", "퇴거")
        page.fill("#message", "퇴거하는데 집주인이 보증금을 안 돌려줘요. 집주인 번호는 010-1234-5678이에요.")
        page.click("#send")
        page.wait_for_selector("#resultCard:not([hidden])", timeout=15000)
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "01_web_cloudfront.png"), full_page=True)

        # 2~5) 터미널 확인 결과
        for name, title, src in [
            ("02_api_curl.png", "curl — CloudFront·API Gateway 호출 결과", "curl.txt"),
            ("03_stack_resources.png", "aws cloudformation — 배포된 리소스", "stack.txt"),
            ("04_storage_iam.png", "aws s3 / iam — 저장소·권한 설정", "storage-iam.txt"),
            ("05_tests.png", "단위 테스트·템플릿 검사", "tests.txt"),
        ]:
            text = (EVID / src).read_text()
            if src == "curl.txt":
                text += "\n$ aws dynamodb query --table-name jachwi-rag-conversations-dev (sessionId=report-test-2)\n"
                text += (EVID / "dynamodb.json").read_text()
            page.set_content(term_html(title, text))
            page.set_viewport_size({"width": 1100, "height": 400})
            page.screenshot(path=str(OUT / name), full_page=True)

        # 6) GitHub 저장소
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(repo, wait_until="networkidle")
        page.screenshot(path=str(OUT / "06_github_repo.png"))
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
