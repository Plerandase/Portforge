# CloudFormation용 IAM 역할 생성

$roleName = "CloudFormation-SecretsManager-Role"
$accountId = "023490709500"

# Trust Policy (CloudFormation이 이 역할을 사용할 수 있도록)
$trustPolicy = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Effect = "Allow"
            Principal = @{
                Service = "cloudformation.amazonaws.com"
            }
            Action = "sts:AssumeRole"
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "1. IAM 역할 생성 중..." -ForegroundColor Yellow

# IAM 역할 생성
aws iam create-role `
    --role-name $roleName `
    --assume-role-policy-document $trustPolicy

Write-Host "2. IAM 정책 생성 및 연결 중..." -ForegroundColor Yellow

# 정책 생성
aws iam create-policy `
    --policy-name "SecretsManager-PortForge-Policy" `
    --policy-document file://cloudformation-role.json

# 정책을 역할에 연결
aws iam attach-role-policy `
    --role-name $roleName `
    --policy-arn "arn:aws:iam::$accountId:policy/SecretsManager-PortForge-Policy"

Write-Host "✅ IAM 역할 생성 완료!" -ForegroundColor Green
Write-Host "역할 ARN: arn:aws:iam::$accountId:role/$roleName" -ForegroundColor Cyan