import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "chat"))
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-2")

import app  # noqa: E402

SECRET = "test-secret-1234567890"


def event(path, method, body=None, secret=SECRET):
    headers = {"X-Origin-Verify": secret} if secret else {}
    return {"path": path, "httpMethod": method, "headers": headers,
            "body": json.dumps(body, ensure_ascii=False) if body is not None else None}


@mock.patch.dict(os.environ, {"ORIGIN_VERIFY_SECRET": SECRET, "TABLE_NAME": "t"})
class HandlerTest(unittest.TestCase):
    def test_mask_pii(self):
        text = "제 번호는 010-1234-5678, 주민번호 990101-1234567, 계좌 110-123-456789 입니다"
        masked, found = app.mask_pii(text)
        self.assertNotIn("5678", masked)
        self.assertNotIn("1234567", masked)
        self.assertNotIn("456789", masked)
        self.assertEqual(found, ["[주민등록번호]", "[전화번호]", "[계좌번호]"])

    def test_mask_pii_followed_by_korean(self):
        masked, found = app.mask_pii("집주인 번호는 010-1234-5678이에요")
        self.assertEqual(masked, "집주인 번호는 [전화번호]이에요")

    def test_mask_pii_keeps_dates(self):
        masked, found = app.mask_pii("2026-11-20에 계약했어요")
        self.assertEqual(found, [])

    def test_rejects_without_cloudfront_header(self):
        res = app.handler(event("/api/health", "GET", secret=None), None)
        self.assertEqual(res["statusCode"], 403)

    def test_health(self):
        res = app.handler(event("/api/health", "GET"), None)
        self.assertEqual(res["statusCode"], 200)
        self.assertEqual(json.loads(res["body"])["status"], "ok")

    def test_chat_stores_masked_message(self):
        table = mock.Mock()
        with mock.patch.object(app, "_get_table", return_value=table):
            res = app.handler(event("/api/chat", "POST", {
                "message": "보증금 안 줘요 010-1111-2222", "contractType": "월세",
                "stage": "퇴거", "region": "경기"}), None)
        self.assertEqual(res["statusCode"], 200)
        stored = table.put_item.call_args.kwargs["Item"]
        self.assertIn("[전화번호]", stored["message"])
        self.assertEqual(stored["expiresAt"] - stored["createdAt"], 30 * 86400)

    def test_chat_validation(self):
        res = app.handler(event("/api/chat", "POST", {"message": ""}), None)
        self.assertEqual(res["statusCode"], 400)
        res = app.handler(event("/api/chat", "POST", {"message": "hi", "stage": "없음"}), None)
        self.assertEqual(res["statusCode"], 400)


if __name__ == "__main__":
    unittest.main()
