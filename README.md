# 安全基线核查平台

## 项目简介

安全基线核查平台是一款自动化安全配置检查工具，支持操作系统、数据库、中间件的安全基线扫描与合规性检查。

### 主要功能

- **操作系统扫描**: 麒麟、CentOS、Ubuntu、Windows 7/10/2012
- **数据库扫描**: 达梦、MySQL、Oracle
- **中间件扫描**: Apache、Nginx、Redis、Tomcat
- **合规标准**: GJB 5621A、GB/T 36960-2018
- **报告生成**: Excel、Word、JSON 格式

### 技术架构

- 后端: Python 3.10 + FastAPI + SQLAlchemy
- 前端: 原生 HTML/CSS/JavaScript
- 数据库: SQLite

---

## 快速开始

### 方式一：开发运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python run.py

# 或指定端口
python run.py -p 8080
```

### 方式二：部署包运行

**Windows:**
```cmd
双击 start.bat
或 start.bat -p 8080
```

**麒麟:**
```bash
./start.sh
或 ./start.sh -p 8080
```

---

## 目录结构

```
baseline-checker/
├── run.py                 # 启动入口
├── app.py                 # 主程序
├── models.py              # 数据模型
├── config.py              # 配置文件
├── requirements.txt       # 依赖列表
│
├── scanners/              # 扫描器模块
│   ├── kylin.py          # 麒麟扫描器
│   ├── dameng.py         # 达梦扫描器
│   ├── mysql.py          # MySQL扫描器
│   ├── oracle.py         # Oracle扫描器
│   ├── apache.py         # Apache扫描器
│   ├── nginx_scanner.py  # Nginx扫描器
│   ├── redis_scanner.py  # Redis扫描器
│   ├── tomcat_scanner.py # Tomcat扫描器
│   ├── windows.py        # Windows扫描器
│   └── linux.py          # Linux通用扫描器
│
├── rules/                 # 规则库
│   ├── kylin/            # 麒麟规则
│   ├── centos/           # CentOS规则
│   ├── ubuntu/           # Ubuntu规则
│   ├── dameng/           # 达梦规则
│   ├── mysql/            # MySQL规则
│   ├── oracle/           # Oracle规则
│   ├── apache/           # Apache规则
│   ├── nginx/            # Nginx规则
│   ├── redis/            # Redis规则
│   ├── tomcat/           # Tomcat规则
│   ├── windows7/         # Windows 7规则
│   ├── windows10/        # Windows 10规则
│   ├── windows2012/      # Windows 2012规则
│   ├── gbt36960/         # GB/T 36960规则
│   ├── gjb5621a/         # GJB 5621A规则
│   └── general/          # 通用信息采集
│
├── modules/               # 功能模块
│   ├── auth.py           # 认证模块
│   ├── executor.py       # 命令执行
│   ├── logger.py         # 日志模块
│   └── report_generator.py # 报告生成
│
├── templates/             # 前端模板
├── static/                # 静态资源
├── database/              # 数据库文件
├── logs/                  # 日志目录
├── reports/               # 报告目录
│
├── scripts/               # 构建脚本
│   ├── build-windows.ps1  # Windows打包
│   └── build-kylin.sh     # 麒麟打包
│
└── docs/                  # 文档目录
    ├── DEPLOY.md         # 部署文档
    ├── RULES.md          # 规则说明
    └── API.md            # API文档
```

---

## 规则库统计

| 类型 | 目标 | 规则数 |
|------|------|--------|
| 操作系统 | 麒麟 | 85 |
| 操作系统 | CentOS | 50 |
| 操作系统 | Ubuntu | 50 |
| 操作系统 | Windows 7/10/2012 | 39 |
| 数据库 | 达梦 | 60 |
| 数据库 | MySQL | 50 |
| 数据库 | Oracle | 50 |
| 中间件 | Apache | 55 |
| 中间件 | Nginx | 55 |
| 中间件 | Redis | 55 |
| 中间件 | Tomcat | 55 |
| 国标 | GB/T 36960 | 20 |
| 国标 | GJB 5621A | 35 |
| 通用 | 信息采集 | 65 |
| **总计** | | **724** |

---

## 支持的检查项

### 身份鉴别
- 密码复杂度策略
- 登录失败锁定
- 用户权限分离
- 默认账户检查

### 访问控制
- 文件权限检查
- 服务端口限制
- 网络访问控制
- 账户权限配置

### 安全审计
- 日志记录配置
- 审计策略检查
- 日志保护机制

### 通信安全
- SSL/TLS配置
- 加密算法检查
- 证书有效性

### 资源控制
- 内存限制
- 连接数限制
- 超时配置

---

## 部署指南

详见 [DEPLOY.md](DEPLOY.md)

### Windows 部署

```powershell
cd scripts
powershell -ExecutionPolicy Bypass -File build-windows.ps1
```

### 麒麟V10 aarch64 部署

```bash
# 上传 build-kylin.sh 到联网麒麟服务器
chmod +x build-kylin.sh
sudo ./build-kylin.sh
```

---

## 默认账号

- 用户名: `admin`
- 密码: `admin123`

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v2.3.0 | 2026-03-12 | 新增中间件扫描(Apache/Nginx/Redis/Tomcat) |
| v2.2.0 | 2026-03-11 | 新增GJB 5621A数据库规则 |
| v2.1.0 | 2026-03-10 | 便携版发布，内置依赖 |

---

## 开发团队

基线核查平台开发团队

## 许可证

内部使用
