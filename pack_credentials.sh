#!/bin/bash
# 生成 GitHub Secret 的值：把本机的 wecom 加密凭证打包并 base64 编码
# 运行： bash pack_credentials.sh
# 生成的 WECOM_CONFIG_SECRET.txt 里就是要在 GitHub 仓库 Secrets 里填入的内容
set -e

if [ -z "$HOME" ]; then echo 'HOME 未设置'; exit 1; fi
if [ ! -d "$HOME/.config/wecom" ]; then
  echo "未找到 $HOME/.config/wecom，请先在本机执行: wecom-cli auth init 完成扫码授权"
  exit 1
fi

tar -czf - -C "$HOME" .config/wecom | base64 -w0 > WECOM_CONFIG_SECRET.txt
echo "已生成 WECOM_CONFIG_SECRET.txt"
echo "请打开该文件，复制【全部内容】，到 GitHub 仓库:"
echo "  Settings > Secrets and variables > Actions > New repository secret"
echo "    Name : WECOM_CONFIG"
echo "    Value: （粘贴文件里的全部内容）"
