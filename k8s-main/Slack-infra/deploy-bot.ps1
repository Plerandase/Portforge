# Infra Bot 배포 스크립트 (PowerShell)

param(
    [string]$Action = "all",  # all, build, push, deploy, rbac
    [string]$Tag = "latest"
)

$ECR_REPO = "023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/infra-bot"
$REGION = "ap-northeast-2"

function Build-Image {
    Write-Host "🔨 Building Docker image..." -ForegroundColor Cyan
    docker build -t infra-bot:$Tag .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Build completed" -ForegroundColor Green
}

function Push-Image {
    Write-Host "🚀 Pushing to ECR..." -ForegroundColor Cyan
    
    # ECR 로그인
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO
    
    # 태그 및 푸시
    docker tag infra-bot:$Tag ${ECR_REPO}:$Tag
    docker push ${ECR_REPO}:$Tag
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Push failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Push completed" -ForegroundColor Green
}

function Deploy-RBAC {
    Write-Host "🔐 Applying RBAC..." -ForegroundColor Cyan
    kubectl apply -f service-account.yaml
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ RBAC apply failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ RBAC applied" -ForegroundColor Green
}

function Deploy-K8s {
    Write-Host "☸️  Deploying to Kubernetes..." -ForegroundColor Cyan
    
    # ConfigMap & Secret
    kubectl apply -f configmap.yaml
    kubectl apply -f secret.yaml
    
    # Deployment
    kubectl apply -f infrabot-deployment.yaml
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Deployment failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ Deployment completed" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Checking pod status..." -ForegroundColor Cyan
    kubectl get pods -l app=infra-bot
    
    Write-Host ""
    Write-Host "📝 To view logs:" -ForegroundColor Yellow
    Write-Host "   kubectl logs -l app=infra-bot -f" -ForegroundColor Gray
}

# 메인 실행
switch ($Action) {
    "build" {
        Build-Image
    }
    "push" {
        Push-Image
    }
    "deploy" {
        Deploy-K8s
    }
    "rbac" {
        Deploy-RBAC
    }
    "all" {
        Build-Image
        Push-Image
        Deploy-RBAC
        Deploy-K8s
    }
    default {
        Write-Host "❌ Unknown action: $Action" -ForegroundColor Red
        Write-Host "Usage: .\deploy-bot.ps1 -Action [all|build|push|deploy|rbac] -Tag [version]" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "🎉 Done!" -ForegroundColor Green
