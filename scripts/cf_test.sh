#!/bin/bash
# CloudflareSpeedTest 执行脚本
#
# 注意：CloudflareSpeedTest 自 v2.3.5 起，发布包内部多了一层顶层目录
# cfst_linux_amd64/，直接 tar -zxf 后二进制并不在根目录。因此这里改为
# 动态定位二进制路径，同时兼容「扁平」与「带顶层目录」两种打包结构。
set -euo pipefail

CFST_URL="https://github.com/XIU2/CloudflareSpeedTest/releases/latest/download/cfst_linux_amd64.tar.gz"
PKG="cfst_linux_amd64.tar.gz"

# 下载 CloudflareSpeedTest
echo "==> 下载 CloudflareSpeedTest"
wget -q -O "$PKG" "$CFST_URL"

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

# cfst 依赖同目录下的 ip.txt 作为测速地址池
if [ ! -f ip.txt ]; then
  echo "缺少 ip.txt（cfst 必需），当前目录文件："
  ls -la
  exit 1
fi

# 运行测速
#   -n 200   延迟测速次数
#   -t 4     延迟测速线程数
#   -dn 5    对延迟最优的前 5 个 IP 做下载测速
#   -dt 10   每个 IP 的下载测速时长（秒）
#
# 注意：不要加 -dd，该参数含义是「禁用下载测速」，会让下载速度一列恒为 0.00，
#       排序随之退化为纯延迟排序，选出的 IP 只代表延迟最低而非带宽最优。
#       启用下载测速后，result.csv 按下载速度降序排列，第 1 行表头、第 2 行即最优。
echo "==> 开始测速"
./cfst -n 200 -t 4 -dn 5 -dt 10 -o result.csv

# 提取最优 IP
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
