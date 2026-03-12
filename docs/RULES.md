# 规则库说明文档

## 规则文件结构

每个目标类型对应一个目录，包含三类规则文件：

```
rules/
├── {target_type}/
│   ├── base.json       # 基础安全检查规则
│   ├── gjb5621a.json   # GJB 5621A 合规规则
│   └── info.json       # 信息收集规则
```

---

## 规则格式

```json
{
    "name": "规则库名称",
    "version": "1.0.0",
    "description": "规则库描述",
    "compliance": ["合规标准"],
    "rules": [
        {
            "id": "唯一标识",
            "name": "规则名称",
            "description": "规则描述",
            "command": "检查命令",
            "expected": "期望值",
            "check_type": "检查类型",
            "severity": "严重程度",
            "category": "分类",
            "remediation": "修复建议",
            "gjb_ref": "国军标引用"
        }
    ]
}
```

---

## 检查类型 (check_type)

| 类型 | 说明 | 示例 |
|------|------|------|
| `contains` | 输出包含期望值 | `expected: "PermitRootLogin no"` |
| `equals` | 输出等于期望值 | `expected: "600"` |
| `not_equals` | 输出不等于期望值 | `expected: "6379"` |
| `in` | 输出在期望值列表中 | `expected: "600,400"` |
| `regex` | 正则匹配 | `expected: "^password.*pam_pwquality"` |
| `not_contains` | 输出不包含期望值 | `expected: "PermitRootLogin yes"` |
| `not_empty` | 输出非空 | - |
| `info` | 仅收集信息 | - |

---

## 严重程度 (severity)

| 级别 | 说明 |
|------|------|
| `high` | 高危 - 必须整改 |
| `medium` | 中危 - 建议整改 |
| `low` | 低危 - 可选整改 |

---

## 规则分类 (category)

### 操作系统规则分类

- `身份鉴别` - 密码策略、登录控制
- `访问控制` - 权限管理、端口控制
- `安全审计` - 日志配置、审计策略
- `通信安全` - 加密通信、证书配置
- `资源控制` - 内存、连接数限制
- `文件权限` - 敏感文件权限检查
- `服务安全` - 服务配置安全
- `账户安全` - 账户管理安全

### 数据库规则分类

- `身份鉴别` - 用户认证、密码策略
- `访问控制` - 权限配置、网络访问
- `安全审计` - 审计日志配置
- `数据安全` - 数据加密、备份
- `资源配置` - 内存、连接池
- `通信安全` - SSL配置

### 中间件规则分类

- `身份鉴别` - 管理员认证
- `访问控制` - 访问限制、端口绑定
- `信息安全` - 版本隐藏、错误页面
- `通信安全` - HTTPS、TLS配置
- `资源控制` - 连接数、超时
- `应用安全` - 部署安全

---

## 规则库统计

### 操作系统规则

| 目标类型 | base | gjb5621a | info | 总计 |
|----------|------|----------|------|------|
| 麒麟 | 30 | 25 | 30 | 85 |
| CentOS | 20 | 15 | 15 | 50 |
| Ubuntu | 20 | 15 | 15 | 50 |
| Windows 7 | 13 | - | 13 | 26 |
| Windows 10 | 13 | - | 13 | 26 |
| Windows 2012 | 13 | - | 13 | 26 |

### 数据库规则

| 目标类型 | base | gjb5621a | info | 总计 |
|----------|------|----------|------|------|
| 达梦 | 20 | 25 | 15 | 60 |
| MySQL | 20 | 25 | 15 | 60 |
| Oracle | 20 | 25 | 15 | 60 |

### 中间件规则

| 目标类型 | base | gjb5621a | info | 总计 |
|----------|------|----------|------|------|
| Apache | 20 | 25 | 10 | 55 |
| Nginx | 20 | 25 | 10 | 55 |
| Redis | 20 | 25 | 10 | 55 |
| Tomcat | 20 | 25 | 10 | 55 |

### 通用规则

| 规则文件 | 规则数 |
|----------|--------|
| linux_info.json | 30 |
| windows_info.json | 25 |
| database_info.json | 10 |
| gbt36960 数据库规则 | 20 |

---

## 添加新规则

### 1. 创建规则文件

```bash
rules/
└── new_target/
    ├── base.json
    ├── gjb5621a.json
    └── info.json
```

### 2. 编写规则

```json
{
    "name": "新目标基础安全基线",
    "version": "1.0.0",
    "description": "新目标安全检查规则",
    "compliance": ["基线安全"],
    "rules": [
        {
            "id": "NEW-001",
            "name": "示例规则",
            "description": "这是一个示例规则",
            "command": "echo test",
            "expected": "test",
            "check_type": "equals",
            "severity": "high",
            "category": "身份鉴别",
            "remediation": "修复建议"
        }
    ]
}
```

### 3. 创建扫描器

参考 `scanners/` 目录下现有扫描器实现。

### 4. 注册扫描器

在 `app.py` 中添加：
```python
from scanners.new_scanner import NewScanner

scanner_map = {
    ...
    "new_target": NewScanner,
}
```

### 5. 更新前端配置

在 `templates/targets.html` 的 `TARGET_TYPES` 中添加新类型。

---

## 规则编写最佳实践

### 命令编写

1. **优先使用通用命令**
   ```bash
   # 好 - 通用
   grep -E "^PermitRootLogin" /etc/ssh/sshd_config
   
   # 避免 - 特定发行版
   cat /etc/kylin-sshd-config
   ```

2. **处理命令不存在的情况**
   ```bash
   grep -E "^setting" /etc/config 2>/dev/null || echo 'NOT_FOUND'
   ```

3. **多路径检查**
   ```bash
   grep "setting" /etc/config /usr/local/config 2>/dev/null || echo 'NOT_FOUND'
   ```

### 期望值设置

1. **精确匹配** - 用于数值、状态
   ```json
   "expected": "600",
   "check_type": "equals"
   ```

2. **包含匹配** - 用于配置项
   ```json
   "expected": "PermitRootLogin no",
   "check_type": "contains"
   ```

3. **排除匹配** - 用于禁止项
   ```json
   "expected": "PermitRootLogin yes",
   "check_type": "not_contains"
   ```

### 修复建议 (remediation)

提供具体可执行的修复命令：

```json
"remediation": "编辑 /etc/ssh/sshd_config，设置 PermitRootLogin no"
```

---

## 合规标准参考

### GJB 5621A - 军用软件安全要求

- 4.3 身份鉴别
- 4.4 访问控制
- 4.5 信息安全
- 5.3 通信安全
- 5.4 安全审计
- 5.5 资源控制
- 5.6 数据安全

### GB/T 36960-2018 - 信息安全技术 数据库安全技术要求

- 用户身份鉴别
- 自主访问控制
- 安全审计
- 数据完整性
- 数据保密性
