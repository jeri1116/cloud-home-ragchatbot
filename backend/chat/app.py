"""질문 처리 Lambda (2주차 버전).

기획서 '질문 답변 흐름'의 ① 질문 입력 단계 중 일부를 먼저 구현한다.
- CloudFront를 거친 요청만 처리 (X-Origin-Verify 헤더 검사)
- 개인정보(전화번호·주민등록번호·계좌번호) 가림
- 대화를 DynamoDB에 30일 TTL로 저장
검색(Knowledge Bases)·답변 생성(Bedrock Claude)은 이후 주차에 연결한다.
"""

import hmac
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone

import boto3

SERVICE = "jachwi-rag-chatbot"
VERSION = "0.2.0"
DISCLAIMER = (
    "법률 자문이 아닌 공식 자료 안내입니다. 구체적인 사안은 "
    "대한법률구조공단(132) 등에 상담하세요."
)

CONTRACT_TYPES = {"월세", "반전세", "전세"}
STAGES = {"집 보기", "계약", "입주", "거주", "퇴거"}
MAX_MESSAGE_LEN = 1000

# 순서 중요: 주민등록번호 → 전화번호 → 계좌번호
PII_PATTERNS = [
    ("[주민등록번호]", re.compile(r"\b\d{6}\s?-\s?[1-8]\d{6}\b")),
    ("[전화번호]", re.compile(r"\b01[016789][-\s.]?\d{3,4}[-\s.]?\d{4}\b")),
    ("[전화번호]", re.compile(r"\b0\d{1,2}[-\s.]\d{3,4}[-\s.]\d{4}\b")),
    ("[계좌번호]", re.compile(r"\b\d{2,6}-\d{2,6}-\d{4,8}(?:-\d{1,6})?\b")),
]

_table = None


def _get_table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _table


def mask_pii(text: str) -> tuple[str, list[str]]:
    """개인정보를 가리고, 가린 항목 종류 목록을 함께 돌려준다."""
    found = []
    for label, pattern in PII_PATTERNS:
        text, n = pattern.subn(label, text)
        if n and label not in found:
            found.append(label)
    return text, found


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def _from_cloudfront(event: dict) -> bool:
    expected = os.environ.get("ORIGIN_VERIFY_SECRET", "")
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    got = headers.get("x-origin-verify", "")
    return bool(expected) and hmac.compare_digest(got, expected)


def health() -> dict:
    return _response(
        200,
        {
            "status": "ok",
            "service": SERVICE,
            "version": VERSION,
            "stage": os.environ.get("STAGE", "local"),
            "region": os.environ.get("AWS_REGION", "local"),
            "time": datetime.now(timezone.utc).isoformat(),
        },
    )


def chat(event: dict) -> dict:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "JSON 형식이 아닙니다."})

    message = str(body.get("message", "")).strip()
    if not message:
        return _response(400, {"error": "질문(message)을 입력하세요."})
    if len(message) > MAX_MESSAGE_LEN:
        return _response(400, {"error": f"질문은 {MAX_MESSAGE_LEN}자 이하로 입력하세요."})

    contract_type = body.get("contractType", "월세")
    stage = body.get("stage", "계약")
    if contract_type not in CONTRACT_TYPES or stage not in STAGES:
        return _response(400, {"error": "계약 유형 또는 단계 값이 올바르지 않습니다."})
    region = str(body.get("region", "전국"))[:20]

    session_id = str(body.get("sessionId") or uuid.uuid4())[:64]
    masked, pii_types = mask_pii(message)

    now = int(time.time())
    ttl_days = int(os.environ.get("CONVERSATION_TTL_DAYS", "30"))
    item = {
        "sessionId": session_id,
        "sk": f"MSG#{now}#{uuid.uuid4().hex[:8]}",
        "message": masked,
        "contractType": contract_type,
        "stage": stage,
        "region": region,
        "createdAt": now,
        "expiresAt": now + ttl_days * 86400,
    }
    _get_table().put_item(Item=item)

    answer = (
        f"[2주차 연결 테스트] '{contract_type} · {stage} · {region}' 상황의 질문을 받았습니다. "
        "아직 공식 자료 검색(RAG)이 연결되지 않아 실제 답변 대신 처리 결과만 보여드립니다."
    )
    return _response(
        200,
        {
            "sessionId": session_id,
            "answer": answer,
            "maskedQuestion": masked,
            "maskedItems": pii_types,
            "context": {"contractType": contract_type, "stage": stage, "region": region},
            "sources": [],
            "stored": {"table": os.environ.get("TABLE_NAME"), "ttlDays": ttl_days},
            "disclaimer": DISCLAIMER,
        },
    )


def handler(event, context):
    if not _from_cloudfront(event):
        return _response(403, {"error": "CloudFront를 거친 요청만 허용됩니다."})

    path = event.get("path", "")
    method = event.get("httpMethod", "")
    if path.endswith("/api/health") and method == "GET":
        return health()
    if path.endswith("/api/chat") and method == "POST":
        return chat(event)
    return _response(404, {"error": "없는 경로입니다."})
