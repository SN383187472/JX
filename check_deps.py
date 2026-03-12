#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
依赖检查脚本 - 便携版
用于检查便携版依赖是否完整
"""
import sys
import os

# 获取当前目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(BASE_DIR, 'lib')

# 优先从lib目录加载依赖
if os.path.exists(LIB_DIR):
    sys.path.insert(0, LIB_DIR)

sys.path.insert(0, BASE_DIR)


def check_dependencies():
    """检查依赖完整性"""
    print("=" * 50)
    print("     Portable Dependency Checker")
    print("=" * 50)
    print()
    
    # Python版本检查
    print(f"Python Version: {sys.version}")
    print(f"Python Path: {sys.executable}")
    print()
    
    # 检查lib目录
    print(f"lib directory: {LIB_DIR}")
    if os.path.exists(LIB_DIR):
        print("  Status: EXISTS [OK]")
    else:
        print("  Status: NOT FOUND [ERROR]")
        print("\n[ERROR] lib directory not found, please copy the full folder")
        return False
    print()
    
    # 核心依赖检查
    print("-" * 50)
    print("Core Dependencies:")
    print("-" * 50)
    
    dependencies = [
        ("fastapi", "FastAPI Web Framework"),
        ("uvicorn", "ASGI Server"),
        ("pydantic", "Data Validation"),
        ("pydantic_core", "Pydantic Core"),
        ("sqlalchemy", "ORM Framework"),
        ("aiosqlite", "Async SQLite"),
        ("paramiko", "SSH Client"),
        ("jinja2", "Template Engine"),
        ("jose", "JWT Handler"),
        ("passlib", "Password Hashing"),
        ("openpyxl", "Excel Handler"),
        ("docx", "Word Handler"),
        ("cryptography", "Crypto Library"),
    ]
    
    failed = []
    for module_name, desc in dependencies:
        try:
            __import__(module_name)
            print(f"  {module_name:15} [OK] {desc}")
        except ImportError as e:
            print(f"  {module_name:15} [MISSING] {desc}")
            failed.append(module_name)
    
    print()
    
    # pydantic_core .pyd文件检查
    print("-" * 50)
    print("pydantic_core compiled files:")
    print("-" * 50)
    
    pydantic_core_dir = os.path.join(LIB_DIR, 'pydantic_core')
    if os.path.exists(pydantic_core_dir):
        pyd_files = [f for f in os.listdir(pydantic_core_dir) if f.endswith('.pyd')]
        if pyd_files:
            for f in pyd_files:
                print(f"  {f} [OK]")
        else:
            print("  [WARNING] No .pyd files found")
            failed.append("pydantic_core .pyd")
    else:
        print("  [ERROR] pydantic_core directory not found")
        failed.append("pydantic_core")
    
    print()
    
    # 结果汇总
    print("=" * 50)
    if failed:
        print(f"Result: {len(failed)} items FAILED")
        print()
        print("Missing modules:", ", ".join(failed))
        print()
        print("Solutions:")
        print("1. Make sure the entire baseline-checker folder is copied")
        print("2. Make sure target Python version is 3.9-3.10")
        print("3. If still fails, run on target machine:")
        print("   pip install fastapi uvicorn pydantic paramiko sqlalchemy aiosqlite")
        return False
    else:
        print("Result: ALL PASSED")
        print()
        print("Dependencies complete. Run start.bat or python run.py to start.")
        return True


if __name__ == '__main__':
    success = check_dependencies()
    input("\nPress Enter to exit...")
    sys.exit(0 if success else 1)
