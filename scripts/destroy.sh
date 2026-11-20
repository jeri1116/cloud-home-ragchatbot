#!/usr/bin/env bash
# 과제 확인이 끝난 뒤 비용이 나가지 않도록 전체 리소스를 삭제한다.
set -euo pipefail
STAGE="${STAGE:-dev}"
STACK="jachwi-rag-chatbot-${STAGE}"
REGION="ap-northeast-2"

read -r -p "스택 $STACK 과 버킷의 모든 파일(이전 버전 포함)을 영구 삭제합니다. 계속할까요? (yes/no) " ans
[ "$ans" = "yes" ] || { echo "취소했습니다."; exit 0; }

out() { aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }

empty_bucket() {
  local b="$1"
  echo "버킷 비우는 중: $b"
  "$(dirname "$0")/../.venv/bin/python" - "$b" "$REGION" <<'PY'
import sys, boto3
b = boto3.resource("s3", region_name=sys.argv[2]).Bucket(sys.argv[1])
b.object_versions.delete()
PY
}

empty_bucket "$(out DocsBucketName)"
empty_bucket "$(out FrontendBucketName)"
"$(dirname "$0")/../.venv/bin/sam" delete --stack-name "$STACK" --region "$REGION" --no-prompts
echo "삭제 완료"
