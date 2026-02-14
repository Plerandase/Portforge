# Slack Monitoring Bot ECR 배포 스크립트 (PowerShell)
# 사용법: .\deploy-to-ecr.ps1

# ===== 설정 =====
$AWS_REGION = "ap-northeast-2"
$ECR_REPOSITORY = "slack-monitoring-bot"
$IMAGE_TAG = "latest"

# ===== AWS 계정 ID 자동 확인 =====
Write-Host "AWS 계정 ID 확인 중..." -ForegroundColor Cyan
$AWS_ACCOUNT_ID = aws sts get-caller-identity --query Account --output text

if (-not $AWS_ACCOUNT_ID) {
    Write-Host "ERROR: AWS 계정 ID를 확인할 수 없습니다. AWS CLI 설정을 확인하세요." -ForegroundColor Red
    Write-Host "aws configure를 실행하여 AWS 자격증명을 설정하세요." -ForegroundColor Yellow
    exit 1
}

Write-Host "AWS 계정 ID: $AWS_ACCOUNT_ID" -ForegroundColor Green

$ECR_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
$FULL_IMAGE_NAME = "$ECR_URI/${ECR_REPOSITORY}:${IMAGE_TAG}"

# ===== Docker 실행 확인 =====
Write-Host "`nDocker 실행 상태 확인 중..." -ForegroundColor Cyan
try {
    docker info | Out-Null
    Write-Host "Docker가 정상적으로 실행 중입니다." -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Desktop이 실행되지 않았습니다." -ForegroundColor Red
    Write-Host "Docker Desktop을 실행한 후 다시 시도하세요." -ForegroundColor Yellow
    exit 1
}

# ===== ECR 리포지토리 확인/생성 =====
Write-Host "`nECR 리포지토리 확인 중..." -ForegroundColor Cyan
$repoExists = aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>$null

if (-not $repoExists) {
    Write-Host "ECR 리포지토리가 없습니다. 생성 중..." -ForegroundColor Yellow
    aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION
    Write-Host "ECR 리포지토리 생성 완료: $ECR_REPOSITORY" -ForegroundColor Green
} else {
    Write-Host "ECR 리포지토리 확인 완료: $ECR_REPOSITORY" -ForegroundColor Green
}

# ===== ECR 로그인 =====
Write-Host "`nECR 로그인 중..." -ForegroundColor Cyan
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ECR 로그인 실패" -ForegroundColor Red
    exit 1
}
Write-Host "ECR 로그인 성공" -ForegroundColor Green

# ===== Docker 이미지 빌드 =====
Write-Host "`nDocker 이미지 빌드 중..." -ForegroundColor Cyan
Write-Host "이미지 이름: slack-monitoring-bot:$IMAGE_TAG" -ForegroundColor Yellow

docker build -t "slack-monitoring-bot:$IMAGE_TAG" .

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker 이미지 빌드 실패" -ForegroundColor Red
    exit 1
}
Write-Host "Docker 이미지 빌드 성공" -ForegroundColor Green

# ===== 이미지 태그 =====
Write-Host "`n이미지 태그 설정 중..." -ForegroundColor Cyan
Write-Host "태그: $FULL_IMAGE_NAME" -ForegroundColor Yellow

docker tag "slack-monitoring-bot:$IMAGE_TAG" $FULL_IMAGE_NAME

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: 이미지 태그 설정 실패" -ForegroundColor Red
    exit 1
}
Write-Host "이미지 태그 설정 성공" -ForegroundColor Green

# ===== ECR에 푸시 =====
Write-Host "`nECR에 이미지 푸시 중..." -ForegroundColor Cyan
Write-Host "푸시 대상: $FULL_IMAGE_NAME" -ForegroundColor Yellow

docker push $FULL_IMAGE_NAME

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ECR 푸시 실패" -ForegroundColor Red
    exit 1
}

# ===== 완료 =====
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "✅ 배포 완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "이미지 URI: $FULL_IMAGE_NAME" -ForegroundColor Cyan
Write-Host "`n다음 단계:" -ForegroundColor Yellow
Write-Host "1. k8s-deployment.yaml 파일에서 이미지 URI 업데이트" -ForegroundColor White
Write-Host "   image: $FULL_IMAGE_NAME" -ForegroundColor Cyan
Write-Host "" -ForegroundColor White
Write-Host "2. EKS에 배포:" -ForegroundColor White
Write-Host "   .\deploy-to-k8s.ps1 \" -ForegroundColor Cyan
Write-Host "     -SlackBotToken 'xoxb-your-token' \" -ForegroundColor Cyan
Write-Host "     -SlackAppToken 'xapp-your-token' \" -ForegroundColor Cyan
Write-Host "     -ClusterName 'your-cluster'" -ForegroundColor Cyan
