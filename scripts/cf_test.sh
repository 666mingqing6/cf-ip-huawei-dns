#!/bin/bash

# 下载 CloudflareSpeedTest
wget -N https://github.com/XIU2/CloudflareSpeedTest/releases/latest/download/cfst_linux_amd64.tar.gz
tar -zxf cfst_linux_amd64.tar.gz
chmod +x cfst

# 运行测速
# 仅进行延迟测速，不进行下载测速，取延迟最低的 Top 1
./cfst -n 200 -t 4 -dn 1 -dd -o result.csv

# 提取最优 IP
BEST_IP=$(sed -n '2p' result.csv | cut -d',' -f1)

if [ -z "$BEST_IP" ]; then
  echo "未能获取到最优 IP，请检查网络或测速工具输出。"
  exit 1
fi

echo "最优 IP: $BEST_IP"
echo "BEST_IP=$BEST_IP" >> $GITHUB_ENV
