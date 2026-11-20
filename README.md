# 자취방 계약 안내 RAG 챗봇 (jachwi-rag-chatbot)

처음 자취하는 대학생이 원룸·오피스텔 월세 계약의 **집 보기 → 계약 → 입주 → 거주 → 퇴거** 단계마다 확인할 것을
법령·공공기관 자료 근거와 출처·기준일과 함께 알려주는 RAG 챗봇입니다.

> 클라우드 아키텍처 실습 과제 · 한양대학교 ERICA
> 현재 단계: **2주차 — AWS 실행 환경·개발 환경 구성** (RAG 검색·답변 생성은 이후 주차에 연결)

## 아키텍처 (2주차 구현 범위)

```
사용자 ──HTTPS──▶ CloudFront ──(OAC)──▶ S3 (프론트엔드, 비공개)
                     │
                     └─ /api/* ──(X-Origin-Verify 헤더)──▶ API Gateway (스로틀링 10rps/20burst)
                                                              │
                                                              ▼
                                                   Lambda 질문 처리 (Python 3.13, arm64)
                                                   · 입력 검사 · 개인정보 가림
                                                              │ (PutItem/Query만 허용)
                                                              ▼
                                                   DynamoDB 대화 저장 (TTL 30일)

S3 문서 저장소: raw/ · pending/ · processed/ · reports/  (버전 관리, KMS 암호화, 퍼블릭 차단, HTTPS 강제)
CloudWatch Logs(14일) · 오류/지연 경보 ──▶ SNS 알림
```

| 구성 요소 | 2주차 | 이후 주차 |
|---|---|---|
| 웹 프론트엔드 | S3 + CloudFront(OAC) 테스트 페이지 | React UI, AWS WAF |
| 백엔드 API | API Gateway + Lambda (`/api/health`, `/api/chat`) | 스트리밍 응답, Guardrails |
| 문서 저장소 | S3 버킷·경로 구성 | 수집·처리 Lambda, EventBridge, Textract, SQS |
| 벡터 검색 | — | Bedrock Knowledge Bases + OpenSearch Serverless |
| 생성 모델 | — | Bedrock Claude, Titan Embeddings V2 |

## 개발 환경

| 도구 | 버전 | 용도 |
|---|---|---|
| Claude Code | 2.1 | AI 코딩 도구 (프로젝트 규칙은 `CLAUDE.md`) |
| AWS CLI | 2.41 | AWS 계정 접근 |
| AWS SAM CLI | 1.174 | 인프라(IaC) 빌드·배포 |
| GitHub CLI / Git | 2.105 / 2.53 | 저장소 관리 |
| Python | 3.13 | Lambda 런타임, 테스트 |

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v   # 단위 테스트
.venv/bin/cfn-lint template.yaml                     # 템플릿 검사
aws configure                                        # 리전: ap-northeast-2
./scripts/deploy.sh                                  # 배포
./scripts/destroy.sh                                 # 전체 삭제 (과제 확인 후)
```

## 확인 방법

```bash
curl https://<CloudFront 주소>/api/health          # 200 {"status":"ok", ...}
curl https://<API Gateway 주소>/api/health         # 403 (CloudFront 우회 차단)
```
