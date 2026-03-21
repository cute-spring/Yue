#!/bin/bash

# 脚本：修复 MTGA 在 macOS 上的“已损坏”提示
# 使用方法：在终端中执行 bash fix_mtga.sh（可能需要 sudo）

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}>>> 开始修复 MTGA 的“已损坏”问题...${NC}"

# 1. 开启“任何来源”权限（需要 sudo）
echo -e "${YELLOW}1. 开启“任何来源”权限...${NC}"
sudo spctl --master-disable
if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✓ 权限已开启${NC}"
else
    echo -e "${RED}   ✗ 开启权限失败，请检查是否有管理员权限${NC}"
    exit 1
fi

# 2. 定位 MTGA 应用
APP_PATH="/Applications/MTGA_GUI.app"
if [ ! -d "$APP_PATH" ]; then
    echo -e "${RED}   未在 /Applications 找到 MTGA_GUI.app，请手动拖入应用程序文件夹后再试${NC}"
    exit 1
fi

# 3. 移除隔离标记
echo -e "${YELLOW}2. 移除隔离标记...${NC}"
sudo xattr -r -d com.apple.quarantine "$APP_PATH"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✓ 隔离标记已移除${NC}"
else
    echo -e "${RED}   ✗ 移除失败${NC}"
    exit 1
fi

# 4. 尝试打开应用
echo -e "${YELLOW}3. 尝试启动 MTGA...${NC}"
open "$APP_PATH"

echo -e "${GREEN}>>> 修复完成！MTGA 正在启动。${NC}"
echo -e "${YELLOW}注意：首次启动后，如果系统提示需要信任 CA 证书，请按 MTGA 官方文档操作。${NC}"