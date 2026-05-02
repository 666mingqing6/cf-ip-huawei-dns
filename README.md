# Cloudflare 优选 IP 自动同步至华为云解析

本项目利用 GitHub Actions 定时运行 CloudflareSpeedTest，并将测速结果中最优的 IP 自动更新到华为云 DNS 解析记录中。

## 准备工作

您需要在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 中添加以下 Secrets：

| Secret 名称 | 说明 |
| :--- | :--- |
| `HUAWEI_AK` | 华为云 Access Key ID |
| `HUAWEI_SK` | 华为云 Secret Access Key |
| `PROJECT_ID` | 华为云项目 ID (可在“我的凭证”中获取) |
| `ZONE_ID` | 华为云解析托管区域 ID |
| `RECORD_ID` | 具体的 A 记录 ID |
| `DOMAIN_NAME` | 您的完整域名 (例如 `pages.example.com`) |

## 如何获取 ID？

您可以运行 `scripts/list_dns_info.py` 来查询您的 `ZONE_ID` 和 `RECORD_ID`。
在本地运行前，请先设置环境变量：
```bash
export HUAWEI_AK="您的AK"
export HUAWEI_SK="您的SK"
python scripts/list_dns_info.py
```

## 自动化计划

默认配置为每 2 小时自动运行一次测速与同步。您可以修改 `.github/workflows/main.yml` 中的 `cron` 表达式来调整频率。
