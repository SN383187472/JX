# 部署指南

## 部署方案概述

本平台支持双平台独立部署，复制后直接运行，无需安装依赖。

| 平台 | 部署包 | 大小 |
|------|--------|------|
| Windows x64 | baseline-checker-windows.zip | ~25 MB |
| 麒麟V10 aarch64 | baseline-checker-kylin-aarch64.tar.gz | ~50 MB |

---

## 快速部署

### Windows

```cmd
1. 解压 baseline-checker-windows.zip
2. 双击 start.bat
3. 浏览器访问 http://localhost:8000
4. 默认账号: admin / admin123

# 自定义端口
start.bat -p 13456

# 后台运行
start.bat -p 8080 -d
```

### 麒麟

```bash
# 1. 解压
tar -xzf baseline-checker-kylin-aarch64.tar.gz

# 2. 运行
cd baseline-checker-kylin-aarch64
./start.sh

# 3. 访问
浏览器打开 http://服务器IP:8000

# 自定义端口
./start.sh -p 13456

# 后台运行
./start.sh -p 8080 -d
```

---

## 构建部署包

### 构建 Windows 部署包

**前置条件:** 需要先下载 Python 3.10 嵌入版（脚本会自动下载）

```powershell
cd C:\project\baseline-checker\scripts
powershell -ExecutionPolicy Bypass -File build-windows.ps1

# 输出: scripts\output\baseline-checker-windows.zip
```

**构建内容:**
- Python 3.10.11 嵌入版 (~10 MB)
- 项目依赖库 (~45 MB)
- 应用程序 (~2 MB)

### 构建麒麟部署包

**在联网的麒麟V10 aarch64服务器上执行:**

```bash
# 1. 上传项目
scp -r baseline-checker root@kylin-server:/tmp/

# 2. 执行构建
cd /tmp/baseline-checker/scripts
chmod +x build-kylin.sh
sudo ./build-kylin.sh

# 输出: scripts/output/baseline-checker-kylin-aarch64.tar.gz
```

---

## 部署包结构

### Windows

```
baseline-checker-windows/
├── python3/                  # Python 3.10 环境
│   ├── python.exe           # 解释器
│   ├── python310.dll        # 运行库
│   ├── python310.zip        # 标准库
│   ├── *.pyd                # 扩展模块
│   └── Lib/site-packages/   # 依赖库
├── app/                      # 应用程序
│   ├── run.py               # 启动入口
│   ├── app.py               # 主程序
│   ├── scanners/            # 扫描器
│   ├── rules/               # 规则库
│   ├── templates/           # 模板
│   └── static/              # 静态资源
└── start.bat                 # 启动脚本
```

### 麒麟

```
baseline-checker-kylin-aarch64/
├── python3/                  # Python 3.10 环境
│   ├── bin/python3          # 解释器
│   └── lib/                 # 标准库+依赖库
├── app/                      # 应用程序
│   ├── run.py
│   ├── scanners/
│   ├── rules/
│   └── ...
└── start.sh                  # 启动脚本
```

---

## 系统要求

### Windows
- Windows 7/10/11 或 Windows Server 2012+
- 内存: 最低 512MB
- 磁盘: 最低 100MB

### 麒麟V10
- 麒麟V10 aarch64
- 内存: 最低 512MB
- 磁盘: 最低 150MB

---

## 防火墙配置

### Windows
```powershell
netsh advfirewall firewall add rule name="BaselineChecker" dir=in action=allow protocol=tcp localport=8000
```

### 麒麟
```bash
firewall-cmd --add-port=8000/tcp --permanent
firewall-cmd --reload
```

---

## 常见问题

### Q: Windows 启动失败？
检查是否被杀毒软件拦截，添加信任目录。

### Q: 麒麟提示 "cannot execute binary file"？
确认部署包架构正确，需要 aarch64 版本。

### Q: 端口被占用？
使用其他端口启动：`start.bat -p 8080`

### Q: 无法访问Web界面？
检查防火墙配置，确保端口开放。

---

## 升级指南

1. 备份数据库: `app/database/baseline.db`
2. 删除旧版本目录
3. 解压新版本
4. 恢复数据库文件到 `app/database/`
