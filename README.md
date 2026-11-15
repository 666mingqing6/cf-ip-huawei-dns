# Cloudflare 优选 IP 自动同步至华为云解析

利用 GitHub Actions 定时运行 [CloudflareSpeedTest](https://github.com/XIU2/CloudflareSpeedTest)，将测速结果中最优的 Cloudflare 边缘 IP 自动写入华为云 DNS 的 A 记录，让域名始终指向当前网络环境下响应最快的 Cloudflare 节点。

> 本项目同步的是 **Cloudflare 优选 IP**，不是你家宽带的动态公网 IP。如需 DDNS（公网 IP 变化后自动改解析），需把测速步骤替换为获取出口 IP 的逻辑。

## 工作原理

1. GitHub Actions 按 `cron` 定时触发（默认每 2 小时）
2. `scripts/cf_test.sh` 下载并运行 CloudflareSpeedTest，产出 `result.csv`
3. 取 CSV 首行的最优 IP，写入 `$GITHUB_ENV` 的 `BEST_IP`
4. `scripts/update_dns.py` 调用华为云 DNS 的 `UpdateRecordSet` 接口，覆盖目标 A 记录

## 快速开始

### 1. 获取代码

Fork 或克隆本仓库到自己的账号下。**必须使用自己的仓库**，否则无法配置自己的 Secrets。

### 2. 配置 Secrets

进入仓库 `Settings → Secrets and variables → Actions → New repository secret`，逐个添加：

| Secret 名称 | 是否必填 | 说明 |
| :--- | :--- | :--- |
| `HUAWEI_AK` | 必填 | 华为云 Access Key ID |
| `HUAWEI_SK` | 必填 | 华为云 Secret Access Key |
| `PROJECT_ID` | 必填 | 华为云项目 ID，须与 `HUAWEI_REGION` 对应 |
| `ZONE_ID` | 单记录模式必填 | 域名托管区域 ID |
| `RECORD_ID` | 单记录模式必填 | 目标 A 记录的 ID |
| `DOMAIN_NAME` | 单记录模式必填 | 完整记录名，如 `pages.example.com`（**不要带末尾的点**） |
| `HUAWEI_REGION` | 选填 | 默认 `cn-north-4`（华北-北京四） |
| `DNS_RECORDS` | 多记录模式必填 | JSON 数组，见「多记录模式」 |

`HUAWEI_AK` / `HUAWEI_SK` 获取：华为云控制台右上角账号名 → **我的凭证** → **访问密钥** → 新增访问密钥（`credentials.csv` 仅可下载一次）。

`PROJECT_ID` 获取：**我的凭证** → **API 凭证** → 项目列表 → 找到 `cn-north-4` 对应行，复制「项目 ID」。

### 3. 启用并首次运行

- 进入 `Actions` 标签页，若提示 workflow 被禁用，点击 **I understand my workflows, go ahead and enable them**
- 选择 `Cloudflare SpeedTest & Huawei DNS Sync` → **Run workflow** 手动触发一次
- 日志中应依次出现 `最优 IP: x.x.x.x` 与 `成功更新域名 ... 解析到 IP: ...`

### 4. 调整执行频率

修改 `.github/workflows/main.yml` 中的 `cron` 表达式（**UTC 时间**）：

| 表达式 | 含义 |
| :--- | :--- |
| `0 */2 * * *` | 每 2 小时整点（默认） |
| `0 * * * *` | 每小时整点 |
| `0 */6 * * *` | 每 6 小时整点 |

## 如何获取 ZONE_ID 与 RECORD_ID

### 方式一：本地脚本（推荐）

```bash
pip install huaweicloudsdkcore huaweicloudsdkdns

export HUAWEI_AK="您的AK"
export HUAWEI_SK="您的SK"
export PROJECT_ID="您的项目ID"   # 可留空，SDK 会自动获取

python scripts/list_dns_info.py
```

Windows PowerShell 写法：

```powershell
$env:HUAWEI_AK="您的AK"; $env:HUAWEI_SK="您的SK"; $env:PROJECT_ID="您的项目ID"
python scripts/list_dns_info.py
```

脚本会打印每个公网域名及其 `ZONE_ID`，并列出该域名下所有 A / CNAME 记录的 `RECORD_ID`。

### 方式二：控制台 + 开发者工具

1. 华为云控制台 → 云解析服务 DNS → 公网解析 → 点击目标域名进入记录集列表
2. 按 `F12` 打开开发者工具 → `Network` 面板 → 刷新页面
3. 找到 `list_record_sets_with_line` 请求，在 Response 中查看：
   - `recordsets[].id` → `RECORD_ID`
   - `zones[].id` → `ZONE_ID`

### 方式三：API Explorer

在华为云 [API Explorer](https://apiexplorer.developer.huaweicloud.com/) 在线调用 `ListPublicZones`（取 Zone ID）与 `ListRecordSetsWithLine`（取 Record ID），无需本地环境。

> **注意**：华为云 API 返回的记录名带结尾的点（如 `pages.example.com.`），填入 `DOMAIN_NAME` 时请去掉。

## 多记录模式

> **⚠️ 优先级说明（最容易踩的坑）**
> `DNS_RECORDS` 一旦非空，`ZONE_ID` / `RECORD_ID` / `DOMAIN_NAME` 会被**完全忽略**。
> 如果你明明配置了单记录 Secrets，运行结果却在更新别的域名，几乎都是因为 `DNS_RECORDS` 里还留着旧值——请到 Secrets 页面删除它，或把它改成正确的记录。
> 脚本启动时会打印当前使用的模式，并在两者同时存在时给出明确警告。

需要同时更新多条 A 记录时，不必填 `ZONE_ID` / `RECORD_ID` / `DOMAIN_NAME`，改用单个 `DNS_RECORDS` secret：

```json
[
  {"zone_id": "xxx", "record_id": "yyy", "domain_name": "a.example.com"},
  {"zone_id": "xxx", "record_id": "zzz", "domain_name": "b.example.com"}
]
```

同一次运行中，所有记录会被更新为**同一个** `BEST_IP`。

## 常见问题

### 定时任务不触发

- Fork 出来的仓库，workflow 默认处于禁用状态，需在 Actions 页面手动启用
- 仓库连续 60 天无提交，GitHub 会自动停用定时任务，需手动 Run 一次保活
- `schedule` 本身不精确，免费 runner 常延迟 5~30 分钟，属正常现象

### 报错 `chmod: cannot access 'cfst': No such file or directory`

CloudflareSpeedTest 自 v2.3.5 起，发布包内部多了一层顶层目录 `cfst_linux_amd64/`，`tar -zxf` 后二进制位于 `./cfst_linux_amd64/cfst` 而非 `./cfst`，同时 `ip.txt` 也不在根目录。

本项目 `scripts/cf_test.sh` 已改为动态定位二进制路径，兼容两种打包结构。若你使用的是旧版脚本，请同步更新，或至少把解压命令改为：

```bash
tar -zxf cfst_linux_amd64.tar.gz --strip-components=1
```

### 更新步骤报错

| 状态码 | 原因 | 处理 |
| :--- | :--- | :--- |
| `401` | AK/SK 错误，或 AK 与 `HUAWEI_REGION` 不匹配 | 核对密钥与区域 |
| `403` | 该 AK 对应的 IAM 用户缺少 DNS 权限 | 授予 `DNS FullAccess` |
| `404` | `ZONE_ID` 与 `RECORD_ID` 不匹配，或记录已删除 | 重新获取 ID |

### 记录里的多个 IP 变成了一个

`update_dns.py` 使用 `body.records = [new_ip]` **整条覆盖**，原有多个值会被清空为一个，TTL 沿用记录原有设置（无则为 300）。若目标记录原本挂有多个 IP，请改用多记录模式拆分为多条记录。

### 为什么下载速度全是 `0.00`？

两个可能原因，按概率排序：

1. **下载测速地址不可用**。`cfst` 默认使用 `https://cf.xiu2.xyz/url`，上游明确说明「默认地址不保证可用性，建议自建」。该地址被阻断、返回 403 或超时，都会导致每个 IP 在极短时间内失败并显示 `0.00`。
2. **脚本带了 `-dd`**。该参数含义是禁用下载测速，加上后 `下载速度` 恒为 `0.00`，排序退化为纯延迟排序。本项目已移除。

排查方式：脚本已开启 `-debug`，日志会直接打印失败原因（403 / 超时 / 地址异常）。若确认是地址问题，在仓库 `Settings → Secrets and variables → Actions → Variables` 新建变量 `CFST_DL_URL`，指向一个 Cloudflare 后端、可直接下载、体积足够大的地址（如你自己域名下的一个大文件），无需改代码。

### 当前测速参数

| 参数 | 含义 | 默认值 |
| :--- | :--- | :--- |
| `-f ip_104.txt` | 指定网段文件，本项目只测 104.x | `ip.txt`（全量 Cloudflare 段） |
| `-n 200` | 延迟测速**线程数**（并发数，非次数） | 200（上限 1000） |
| `-t 4` | 单个 IP 的延迟测速**次数** | 4 |
| `-dn 5` | 按延迟排序后，对前 N 个 IP 做下载测速 | 10 |
| `-dt 10` | 单个 IP 的下载测速最长时长（秒） | 10 |
| `-url` | 下载测速地址 | `https://cf.xiu2.xyz/url` |
| `-debug` | 下载测速失败时输出具体原因 | 关闭 |
| `-dd` | **禁用下载测速（本项目不使用）** | — |

> 注意区分两个易混淆的参数：`-tl` 是**平均延迟上限**（毫秒），`-sl` 才是**下载速度下限**（MB/s）。若想只保留带宽达标的 IP，用 `-sl 5`；若想过滤掉回源的 IP（下载速度 0.00），用 `-sl 0.01`。

## 测速网段配置

网段由仓库根目录的 `ip_104.txt` 控制，当前内容：

```
104.16.0.0/13
104.24.0.0/14
```

这两段合起来覆盖 `104.16.0.0 ~ 104.27.255.255`，是 Cloudflare 官方公布的 104.x 段（见 [cloudflare.com/ips-v4](https://www.cloudflare.com/ips-v4)）。

`cfst` 默认对每个 `/24` 随机取一个 IP 测速，因此该配置的候选 IP 约 3072 个；如需对段内每个 IP 逐一测速，加 `-allip`（会显著增加耗时）。

若想扩大或缩小范围，直接改这个文件即可：

| 目标 | 写法 |
| :--- | :--- |
| 只要 104.16~104.23 | `104.16.0.0/13` |
| 加入其他 Cloudflare 段 | 追加 `172.64.0.0/13`、`162.158.0.0/15` 等 |
| 恢复全量测速 | 删掉脚本里的 `-f "$IP_LIST"`，改用包内自带 `ip.txt` |

### 测速结果是否适合中国大陆访问

GitHub Actions 的 runner 位于海外机房，测出的「最优 IP」反映的是该机房到 Cloudflare 的延迟，对大陆访问者的参考价值有限。若主要用户在中国大陆，建议在本机或国内 VPS 上测速后自行维护 IP 列表。

### 安全建议

- 不要使用主账号 AK/SK。建议创建 IAM 子用户（勾选「编程访问」），仅授予 `DNS FullAccess`
- 仓库建议设为 Private，避免 Secrets 配置与域名信息外泄
- AK/SK 一旦在公开渠道出现过，应立即在控制台禁用并重新生成

## 目录结构

```
.
├── .github/workflows/main.yml   # 定时任务定义
├── scripts/
│   ├── cf_test.sh               # 下载并运行 CloudflareSpeedTest
│   ├── list_dns_info.py         # 查询 ZONE_ID / RECORD_ID
│   └── update_dns.py            # 调用华为云 DNS 更新记录
├── ip_104.txt                   # 测速网段（仅 Cloudflare 104.x）
├── requirements.txt
└── README.md
```

## 更新记录

- **2026-11-16（三次）**：测速网段收敛到 Cloudflare 104.x（新增 `ip_104.txt`，脚本改用 `-f`）；下载测速地址支持通过 `CFST_DL_URL` 变量覆盖；开启 `-debug` 输出下载失败原因；修正 README 中 `-n`/`-t`/`-tl`/`-sl` 的参数说明错误
- **2026-11-16（二次）**：`cf_test.sh` 移除 `-dd`，启用下载测速（`-dn 5 -dt 10`），最优 IP 改按下载速度排序；`update_dns.py` 增加模式显式提示、重复条目去重、更新前存在性校验（404 直接指出 ID 失效）、保留原有 TTL、当前值相同则跳过；README 补充模式优先级与测速参数说明
- **2026-11-16**：修复 cfst 发布包目录结构变更导致的解压失败；补充 `ip.txt` 与 IP 格式校验；重写 README
- **2026-05-02**：支持多条 DNS 记录（`DNS_RECORDS`），整理项目结构
