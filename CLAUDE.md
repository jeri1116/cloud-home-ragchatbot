# 자취방 계약 안내 RAG 챗봇

처음 자취하는 대학생에게 월세 계약 단계별 확인 사항을 법령·공공기관 자료 근거와 함께 안내하는 RAG 챗봇.
설계 원본: `../클라우드아키텍처-RAG_챗봇_서비스_기획서_조희연.docx` (1주차 기획서)

## 구조
- `template.yaml` — AWS SAM 템플릿 (서울 리전 ap-northeast-2). 모든 인프라는 여기서만 변경한다.
- `backend/chat/app.py` — 질문 처리 Lambda (Python 3.13, arm64)
- `frontend/` — S3 + CloudFront로 제공하는 정적 페이지 (`/api/*`는 CloudFront가 API Gateway로 전달)
- `scripts/deploy.sh`, `scripts/destroy.sh` — 배포 / 전체 삭제

## 명령
- 테스트: `.venv/bin/python -m unittest discover -s tests -v`
- 템플릿 검사: `.venv/bin/cfn-lint template.yaml`
- 배포: `./scripts/deploy.sh`

## 규칙
- Lambda IAM 권한은 필요한 리소스·액션만 (최소 권한). `*` 리소스 금지.
- S3 버킷은 퍼블릭 액세스 차단 유지. 프론트엔드는 CloudFront OAC로만 읽는다.
- API는 CloudFront 비밀 헤더(X-Origin-Verify)가 있는 요청만 처리한다.
- 사용자 질문은 개인정보를 가린 뒤 저장·전달한다. 대화는 DynamoDB TTL 30일.
- 답변에는 항상 안내 문구(법률 자문 아님, 132 상담)를 붙인다.
