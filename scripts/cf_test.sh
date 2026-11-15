#!/bin/bash
# CloudflareSpeedTest 执行脚本
#
# 说明：
#   1. CloudflareSpeedTest 自 v2.3.5 起，发布包内部多了一层顶层目录
#      cfst_linux_amd64/，因此这里动态定位二进制路径，兼容两种打包结构。
#   2. 测速网段由仓库根目录的 ip_104.txt 指定，当前仅覆盖 Cloudflare 的 104.x 段。
#   3. 下载测速地址默认用 cfst 官方地址，可通过仓库变量 CFST_DL_URL 覆盖。
set -euo pipefail

CFST_PKG_URL="https://github.com/XIU2/CloudflareSpeedTest/releases/latest/download/cfst_linux_amd64.tar.gz"
PKG="cfst_linux_amd64.tar.gz"
IP_LIST="ip_104.txt"

# 下载 CloudflareSpeedTest
echo "==> 下载 CloudflareSpeedTest"
wget -q -O "$PKG" "$CFST_PKG_URL"

# 解压
echo "==> 解压"
rm -rf _cfst_pkg
mkdir -p _cfst_pkg
tar -zxf "$PKG" -C _cfst_pkg

# 兼容两种打包结构：二进制位于解压根目录，或位于顶层子目录内
CFST_BIN="$(find _cfst_pkg -maxdepth 3 -type f -name cfst | head -n 1 || true)"
if [ -z "${CFST_BIN}" ]; then
  echo "解压后未找到 cfst 可执行文件。压缩包实际内容："
  find _cfst_pkg -maxdepth 3 -type f
  exit 1
fi

CFST_DIR="$(dirname "$CFST_BIN")"
cp -f "$CFST_DIR"/* . 2>/dev/null || true
chmod +x ./cfst

# 校验网段文件
if [ ! -f "$IP_LIST" ]; then
  echo "缺少网段文件 $IP_LIST，当前目录文件："
  ls -la
  exit 1
fi

# 下载测速地址：默认 cfst 官方地址，可用仓库变量 CFST_DL_URL 覆盖（建议自建大文件地址）
DL_URL="${CFST_DL_URL:-https://cf.xiu2.xyz/url}"

# 运行测速
#   -f       指定网段文件（默认 ip.txt，本项目改为 ip_104.txt，只测 104.x）
#   -n 200   延迟测速线程数（默认 200，最大 1000；注意是线程数，不是次数）
#   -t 4     单个 IP 的延迟测速次数（默认 4）
#   -dn 5    按延迟排序后，对前 5 个 IP 做下载测速
#   -dt 10   单个 IP 的下载测速最长时长（秒）
#   -url     下载测速地址
#   -debug   下载测速失败时输出具体原因（403 / 超时 / 地址不可用等）
#   -o       结果文件
#
# 不要加 -dd：它表示「禁用下载测速」，会让下载速度恒为 0.00，排序退化为纯延迟排序。
echo "==> 开始测速"
echo "    网段文件：$IP_LIST"
echo "    下载地址：$DL_URL"
./cfst -f "$IP_LIST" -n 200 -t 4 -dn 5 -dt 10 -url "$DL_URL" -debug -o result.csv

# 输出结果预览
echo "==> 测速结果 Top 3（按下载速度降序）"
head -n 4 result.csv 2>/dev/null || true

echo "==> 提取最优 IP"
BEST_IP="$(sed -n '2p' result.csv | cut -d',' -f1 | tr -d '\r\n ' || true)"

# 校验格式，避免把 CSV 表头当成 IP 写进解析记录
if ! echo "$BEST_IP" | grep -qE '^([0-9]{1,3}\.){3}[0-9]{1,3}$'; then
  echo "未能获取到合法的最优 IP，实际取到: [${BEST_IP}]"
  echo "--- result.csv 前 5 行 ---"
  head -n 5 result.csv 2>/dev/null || echo "(result.csv 不存在)"
  exit 1
fi

echo "最优 IP: ${BEST_IP}"
echo "BEST_IP=${BEST_IP}" >> "$GITHUB_ENV"
