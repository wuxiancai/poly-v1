#!/bin/bash

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 版本检查函数
check_drivers() {
    # 获取Chrome完整版本号（例如：133.0.6943.53）
    CHROME_FULL_VERSION=$(/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version | awk '{print $3}')
    CHROME_MAJOR_VERSION=$(echo "$CHROME_FULL_VERSION" | cut -d'.' -f1)  # 只取主版本号
    echo -e "${YELLOW}检测到Chrome版本: ${CHROME_FULL_VERSION}${NC}"

    # 检查chromedriver安装状态
    check_driver() {
        # 检查常见安装路径
        PATHS=("/opt/homebrew/bin/chromedriver" "/usr/local/bin/chromedriver")
        for path in "${PATHS[@]}"; do
            if [ -f "$path" ]; then
                DRIVER_PATH="$path"
                break
            fi
        done

        if [ -z "$DRIVER_PATH" ]; then
            echo -e "${RED}未找到chromedriver安装路径${NC}"
            return 1
        fi
        
        DRIVER_VERSION=$($DRIVER_PATH --version | awk '{print $2}')
        DRIVER_MAJOR_VERSION=$(echo "$DRIVER_VERSION" | cut -d'.' -f1)
        echo -e "${YELLOW}当前chromedriver版本: ${DRIVER_VERSION}${NC}"
        
        # 新的版本比较逻辑：只有当驱动版本小于Chrome版本时才需要更新
        if [ "$DRIVER_MAJOR_VERSION" -lt "$CHROME_MAJOR_VERSION" ]; then
            echo -e "${RED}驱动版本过低，需要更新！${NC}"
            return 1
        fi
        echo -e "${GREEN}驱动版本兼容！${NC}"
        return 0
    }

    # 自动安装驱动
    install_driver() {
        echo -e "${YELLOW}正在使用Homebrew安装chromedriver...${NC}"
        # 先尝试更新
        brew upgrade --cask chromedriver 2>/dev/null || brew install --cask chromedriver
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}驱动安装/更新成功！${NC}"
            return 0
        else
            echo -e "${RED}驱动安装失败！${NC}"
            return 1
        fi
    }

    # 执行版本检查
    if ! check_driver; then
        echo -e "${YELLOW}正在尝试自动更新驱动...${NC}"
        if install_driver; then
            if check_driver; then
                echo -e "${GREEN}版本兼容性问题已解决！${NC}"
            else
                echo -e "${RED}更新后版本仍不兼容！${NC}"
                return 1
            fi
        else
            echo -e "${RED}自动更新失败！${NC}"
            return 1
        fi
    fi

    # 更新PATH环境变量
    export PATH="/usr/local/bin:$PATH"
}

# 主执行流程
echo -e "${YELLOW}开始执行浏览器启动流程...${NC}"

# 先执行驱动检查
if ! check_drivers; then
    echo -e "${RED}驱动检查失败，退出脚本！${NC}"
    exit 1
fi

# 启动Chrome
echo -e "${YELLOW}正在启动Chrome...${NC}"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --remote-debugging-port=9222 \
    --user-data-dir="$HOME/ChromeDebug" \
    https://polymarket.com/markets/crypto

echo -e "${GREEN}Chrome已成功启动！${NC}"