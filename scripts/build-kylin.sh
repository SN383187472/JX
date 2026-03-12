#!/bin/bash
# ========================================
# 麒麟V10 aarch64 完整打包脚本
# 输出: baseline-checker-kylin-aarch64.tar.gz
# ========================================

set -e

PYTHON_VERSION="3.10.14"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="${SCRIPT_DIR}/output"
DEPLOY_DIR="${OUTPUT_DIR}/baseline-checker-kylin-aarch64"
PYTHON_PREFIX="${DEPLOY_DIR}/python3"
APP_DIR="${DEPLOY_DIR}/app"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

banner() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  基线核查平台 - 麒麟打包工具${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
}

check_env() {
    ARCH=$(uname -m)
    if [ "$ARCH" != "aarch64" ]; then
        echo -e "${RED}[错误] 需要在 aarch64 架构上运行${NC}"
        exit 1
    fi
    
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}[错误] 需要 root 权限${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}[信息] 架构: $ARCH${NC}"
    echo -e "${BLUE}[信息] 项目: $PROJECT_DIR${NC}"
    echo ""
}

install_deps() {
    echo -e "${YELLOW}[步骤1/6] 安装编译依赖...${NC}"
    yum install -y gcc make zlib-devel openssl-devel readline-devel \
        sqlite-devel bzip2-devel libffi-devel ncurses-devel gdbm-devel \
        xz-devel tk-devel wget curl tar patchelf 2>/dev/null || \
    dnf install -y gcc make zlib-devel openssl-devel readline-devel \
        sqlite-devel bzip2-devel libffi-devel ncurses-devel gdbm-devel \
        xz-devel tk-devel wget curl tar patchelf 2>/dev/null
    echo -e "${GREEN}[完成]${NC}"
}

build_python() {
    echo -e "${YELLOW}[步骤2/6] 编译Python ${PYTHON_VERSION}...${NC}"
    
    BUILD_DIR="/tmp/python-build"
    rm -rf ${BUILD_DIR} ${OUTPUT_DIR}
    mkdir -p ${BUILD_DIR} ${OUTPUT_DIR} ${DEPLOY_DIR}
    
    cd ${BUILD_DIR}
    
    # 下载Python
    if [ ! -f "Python-${PYTHON_VERSION}.tgz" ]; then
        wget -q --show-progress \
            https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz
    fi
    
    tar -xzf Python-${PYTHON_VERSION}.tgz
    cd Python-${PYTHON_VERSION}
    
    # 编译 (关键: 相对路径RPATH)
    export LDFLAGS="-Wl,-rpath,'\$\$ORIGIN/lib'"
    export CFLAGS="-fPIC -O2"
    
    ./configure --prefix=${PYTHON_PREFIX} \
        --enable-shared \
        --enable-optimizations \
        --with-lto \
        --with-ensurepip=install \
        LDFLAGS="-Wl,-rpath,'\$\$ORIGIN/lib'" \
        > /dev/null
    
    make -j$(nproc) > /dev/null
    make install > /dev/null
    
    echo -e "${GREEN}[完成]${NC}"
}

install_packages() {
    echo -e "${YELLOW}[步骤3/6] 安装Python依赖...${NC}"
    
    ${PYTHON_PREFIX}/bin/python3 -m pip install --upgrade pip -q \
        -i https://pypi.tuna.tsinghua.edu.cn/simple
    
    ${PYTHON_PREFIX}/bin/python3 -m pip install \
        fastapi uvicorn sqlalchemy aiosqlite jinja2 \
        python-multipart passlib bcrypt python-jose \
        paramiko pydantic pydantic-settings \
        openpyxl python-docx cryptography cffi \
        requests pyyaml \
        -i https://pypi.tuna.tsinghua.edu.cn/simple -q
    
    echo -e "${GREEN}[完成]${NC}"
}

copy_libs() {
    echo -e "${YELLOW}[步骤4/6] 复制系统动态库...${NC}"
    
    mkdir -p ${PYTHON_PREFIX}/lib/sys
    
    # 复制依赖库
    ldd ${PYTHON_PREFIX}/bin/python3.10 2>/dev/null | \
        grep "=> /" | awk '{print $3}' | \
        while read lib; do
            [ -f "$lib" ] && cp -v "$lib" ${PYTHON_PREFIX}/lib/sys/ 2>/dev/null || true
        done
    
    find ${PYTHON_PREFIX}/lib/python3.10 -name "*.so" 2>/dev/null | \
        while read so; do
            ldd "$so" 2>/dev/null | grep "=> /" | awk '{print $3}' | \
                while read lib; do
                    [ -f "$lib" ] && cp -v "$lib" ${PYTHON_PREFIX}/lib/sys/ 2>/dev/null || true
                done
        done
    
    # 修复RPATH
    patchelf --set-rpath '$ORIGIN/lib:$ORIGIN/lib/sys' \
        ${PYTHON_PREFIX}/bin/python3.10 2>/dev/null || true
    
    find ${PYTHON_PREFIX}/lib -name "*.so" -type f | \
        while read so; do
            patchelf --set-rpath '$ORIGIN:$ORIGIN/sys' "$so" 2>/dev/null || true
        done
    
    echo -e "${GREEN}[完成]${NC}"
}

copy_app() {
    echo -e "${YELLOW}[步骤5/6] 复制应用程序...${NC}"
    
    rsync -av --exclude='lib' --exclude='pack' --exclude='deploy' \
        --exclude='scripts' --exclude='.git' --exclude='__pycache__' \
        --exclude='*.log' --exclude='*.db' --exclude='*.pyc' \
        ${PROJECT_DIR}/ ${APP_DIR}/ 2>/dev/null || \
    cp -r ${PROJECT_DIR}/* ${APP_DIR}/
    
    # 清理
    rm -rf ${APP_DIR}/lib ${APP_DIR}/pack ${APP_DIR}/deploy ${APP_DIR}/scripts 2>/dev/null || true
    
    echo -e "${GREEN}[完成]${NC}"
}

create_scripts() {
    echo -e "${YELLOW}[步骤6/6] 创建启动脚本...${NC}"
    
    # 启动脚本
    cat > ${DEPLOY_DIR}/start.sh << 'SCRIPT'
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_DIR="${SCRIPT_DIR}/python3"
APP_DIR="${SCRIPT_DIR}/app"
PORT=8000
DAEMON=0

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port) PORT="$2"; shift 2 ;;
        -d|--daemon) DAEMON=1; shift ;;
        -s|--stop) pkill -f "python.*run.py"; echo "已停止"; exit 0 ;;
        -h|--help) echo "用法: $0 [-p 端口] [-d] [-s]"; exit 0 ;;
        *) shift ;;
    esac
done

export LD_LIBRARY_PATH="${PYTHON_DIR}/lib:${PYTHON_DIR}/lib/sys:${LD_LIBRARY_PATH}"
cd "${APP_DIR}"
mkdir -p database logs reports

echo ""
echo "========================================"
echo "   安全基线核查平台 (麒麟版)"
echo "========================================"
echo ""
echo "端口: ${PORT}"
echo "访问: http://localhost:${PORT}"
echo "账号: admin / admin123"
echo ""

if [ "$DAEMON" -eq 1 ]; then
    nohup ${PYTHON_DIR}/bin/python3 run.py --port ${PORT} > logs/app.log 2>&1 &
    echo "[后台运行] 日志: logs/app.log"
else
    exec ${PYTHON_DIR}/bin/python3 run.py --port ${PORT}
fi
SCRIPT
    chmod +x ${DEPLOY_DIR}/start.sh
    
    # README
    cat > ${DEPLOY_DIR}/README.txt << 'README'
========================================
  安全基线核查平台 (麒麟版)
========================================

【快速开始】

1. 启动服务:
   ./start.sh

2. 指定端口:
   ./start.sh -p 8080

3. 后台运行:
   ./start.sh -p 8080 -d

4. 停止服务:
   ./start.sh -s

【访问地址】
http://服务器IP:8000

【默认账号】
用户名: admin
密码: admin123

【目录说明】
├── python3/     Python运行环境
├── app/         应用程序
├── start.sh     启动脚本
└── README.txt   本文件

========================================
README

    echo -e "${GREEN}[完成]${NC}"
}

pack() {
    echo ""
    echo -e "${YELLOW}打包中...${NC}"
    
    # 清理
    find ${DEPLOY_DIR} -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find ${DEPLOY_DIR} -name "*.pyc" -delete 2>/dev/null || true
    rm -rf /tmp/python-build
    
    # 打包
    cd ${OUTPUT_DIR}
    tar -czf baseline-checker-kylin-aarch64.tar.gz baseline-checker-kylin-aarch64
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  打包完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    TOTAL_SIZE=$(du -sh ${DEPLOY_DIR} | awk '{print $1}')
    TAR_SIZE=$(ls -lh ${OUTPUT_DIR}/baseline-checker-kylin-aarch64.tar.gz | awk '{print $5}')
    
    echo "输出: ${OUTPUT_DIR}/baseline-checker-kylin-aarch64.tar.gz"
    echo "大小: ${TAR_SIZE} (解压后 ${TOTAL_SIZE})"
    echo ""
    echo "部署方法:"
    echo "  1. 传输到目标服务器"
    echo "  2. tar -xzf baseline-checker-kylin-aarch64.tar.gz"
    echo "  3. cd baseline-checker-kylin-aarch64"
    echo "  4. ./start.sh"
    echo ""
}

main() {
    banner
    check_env
    install_deps
    build_python
    install_packages
    copy_libs
    copy_app
    create_scripts
    pack
}

main
