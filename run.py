#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基线核查平台启动脚本 - 便携版
支持 Python 3.9 - 3.10
所有依赖已内置，复制即可运行
"""
import sys
import os
import argparse
import socket

# 获取当前目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 便携模式：优先从lib目录加载依赖（必须在导入其他模块前）
LIB_DIR = os.path.join(BASE_DIR, 'lib')
if os.path.exists(LIB_DIR):
    sys.path.insert(0, LIB_DIR)

sys.path.insert(0, BASE_DIR)

# 创建必要目录
os.makedirs(os.path.join(BASE_DIR, 'database'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'reports'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)


def check_port(host, port):
    """检查端口是否被占用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.close()
        return True  # 绑定成功，端口可用
    except OSError:
        return False  # 绑定失败，端口被占用


def main():
    """启动服务"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='安全基线核查平台')
    parser.add_argument('-p', '--port', type=int, default=8000, help='服务端口 (默认: 8000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='绑定地址 (默认: 0.0.0.0)')
    args = parser.parse_args()
    
    print()
    print("=" * 50)
    print("     安全基线核查平台 (便携版)")
    print("=" * 50)
    print()
    
    # 尝试导入fastapi验证依赖
    try:
        import fastapi
        import uvicorn
    except ImportError as e:
        print(f"  [错误] 依赖加载失败: {e}")
        print()
        print("  lib目录可能损坏，请重新下载完整版本")
        print("  或运行 python check_deps.py 检查依赖")
        print()
        input("按回车键退出...")
        return 1
    
    # 检查端口是否被占用
    if not check_port(args.host, args.port):
        print(f"  [错误] 端口 {args.port} 已被占用")
        print()
        print("  请使用其他端口，例如:")
        print(f"    python run.py -p 8001")
        print(f"    start.bat 8001")
        print()
        input("按回车键退出...")
        return 1
    
    print(f"  访问地址: http://localhost:{args.port}")
    print("  默认账号: admin")
    print("  默认密码: admin123")
    print()
    print("  按 Ctrl+C 停止服务")
    print()
    
    try:
        uvicorn.run(
            "app:app",
            host=args.host,
            port=args.port
        )
    except Exception as e:
        print(f"  [错误] 启动失败: {e}")
        input("按回车键退出...")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
