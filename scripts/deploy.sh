#!/usr/bin/env bash
# 서울 리전(ap-northeast-2)에 인프라를 배포하고 테스트 페이지를 올린다.
set -euo pipefail
# Homebrew AWS CLI(Python 3.15)가 시스템 expat 대신 Homebrew expat을 쓰도록
[ -d /opt/homebrew/opt/expat/lib ] && export DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib
cd "$(dirname "$0")/.."
SAM=".venv/bin/sam"

STAGE="${STAGE:-dev}"
STACK="jachwi-rag-chatbot-${STAGE}"
REGION="ap-northeast-2"
ALERT_EMAIL="${ALERT_EMAIL:-}"

# CloudFront → API Gateway 비밀 헤더 (배포마다 새로 만들어 CloudFront와 Lambda에 같이 반영)
SECRET="$(openssl rand -hex 24)"

PARAMS=("Stage=$STAGE" "OriginVerifySecret=$SECRET")
[ -n "$ALERT_EMAIL" ] && PARAMS+=("AlertEmail=$ALERT_EMAIL")

"$SAM" build --template template.yaml
"$SAM" deploy \
  --stack-name "$STACK" \
  --region "$REGION" \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --parameter-overrides "${PARAMS[@]}" \
  --tags project=jachwi-rag-chatbot course=cloud-architecture

out() { aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }

WEB_BUCKET="$(out FrontendBucketName)"
DOCS_BUCKET="$(out DocsBucketName)"
DIST_ID="$(out DistributionId)"
URL="$(out WebsiteUrl)"

# 문서 저장소 경로 만들기 (raw/ pending/ processed/ reports/)
for p in raw/ pending/ processed/ reports/; do
  aws s3api put-object --bucket "$DOCS_BUCKET" --key "$p" --region "$REGION" >/dev/null
done

aws s3 sync frontend/ "s3://$WEB_BUCKET/" --delete --region "$REGION"
aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" >/dev/null

echo
echo "배포 완료: $URL"
echo "(CloudFront 첫 배포는 전파에 몇 분 걸릴 수 있습니다)"
