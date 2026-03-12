# API 接口文档

## 基础信息

- 基础路径: `http://localhost:8000`
- 认证方式: JWT Token (Cookie)
- 内容类型: `application/json` / `multipart/form-data`

---

## 认证接口

### 登录

```
POST /api/login
Content-Type: multipart/form-data
```

**参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**响应:**
```json
{
    "success": true,
    "token": "jwt_token_string"
}
```

### 登出

```
POST /api/logout
```

**响应:**
```json
{
    "success": true
}
```

---

## 目标管理接口

### 获取目标列表

```
GET /api/targets
```

**响应:**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "name": "生产服务器1",
            "host": "192.168.1.100",
            "port": 22,
            "target_type": "kylin",
            "username": "root",
            "created_at": "2026-03-12T10:00:00"
        }
    ]
}
```

### 创建目标

```
POST /api/targets
Content-Type: multipart/form-data
```

**参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 目标名称 |
| host | string | 是 | 主机地址 |
| port | int | 是 | SSH/WinRM端口 |
| target_type | string | 是 | 目标类型 |
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |
| db_port | int | 否 | 数据库端口 |
| db_username | string | 否 | 数据库用户名 |
| db_password | string | 否 | 数据库密码 |
| db_name | string | 否 | 数据库名 |

**目标类型:**
- 操作系统: `kylin`, `centos`, `ubuntu`, `windows7`, `windows10`, `windows2012`
- 数据库: `dameng`, `mysql`, `oracle`
- 中间件: `apache`, `nginx`, `redis`, `tomcat`

**响应:**
```json
{
    "success": true,
    "message": "目标创建成功",
    "id": 1
}
```

### 更新目标

```
PUT /api/targets/{target_id}
```

参数同创建目标。

### 删除目标

```
DELETE /api/targets/{target_id}
```

**响应:**
```json
{
    "success": true,
    "message": "目标已删除"
}
```

### 测试连接

```
POST /api/test-connection
```

参数同创建目标。

**响应:**
```json
{
    "success": true,
    "message": "成功连接到 192.168.1.100"
}
```

---

## 扫描接口

### 获取规则列表

```
GET /api/rules/{target_type}
```

**响应:**
```json
{
    "success": true,
    "data": [
        {
            "filename": "base.json",
            "name": "基础安全基线",
            "rule_count": 30,
            "category": "专属规则"
        }
    ]
}
```

### 执行扫描

```
POST /api/scan
Content-Type: multipart/form-data
```

**参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| target_id | int | 是 | 目标ID |
| rule_file | string | 是 | 规则文件名 |

**响应:**
```json
{
    "success": true,
    "message": "扫描完成",
    "summary": {
        "total": 30,
        "passed": 25,
        "failed": 5
    },
    "result_id": 1
}
```

---

## 结果接口

### 获取结果列表

```
GET /api/results
```

**响应:**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "target_name": "生产服务器1",
            "target_type": "kylin",
            "scan_time": "2026-03-12T10:00:00",
            "total_rules": 30,
            "passed_rules": 25,
            "failed_rules": 5
        }
    ]
}
```

### 获取结果详情

```
GET /api/results/{result_id}
```

**响应:**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "target_name": "生产服务器1",
        "target_type": "kylin",
        "scan_time": "2026-03-12T10:00:00",
        "total_rules": 30,
        "passed_rules": 25,
        "failed_rules": 5,
        "details": [
            {
                "rule_id": "KYLIN-001",
                "rule_name": "SSH Root登录限制",
                "description": "禁止root用户直接SSH登录",
                "status": "pass",
                "command": "grep ...",
                "output": "PermitRootLogin no",
                "expected": "PermitRootLogin no",
                "actual": "PermitRootLogin no",
                "analysis": "期望包含 'PermitRootLogin no'，符合",
                "severity": "high",
                "category": "身份鉴别"
            }
        ]
    }
}
```

### 删除结果

```
DELETE /api/results/{result_id}
```

### 批量删除结果

```
POST /api/results/batch-delete
Content-Type: application/json
```

**请求体:**
```json
{
    "ids": [1, 2, 3]
}
```

---

## 报告接口

### 下载报告

```
GET /api/results/{result_id}/download?format={format}
```

**参数:**
| 参数 | 类型 | 说明 |
|------|------|------|
| format | string | 报告格式: `excel`, `word`, `json` |

**响应:** 文件下载

---

## 页面路由

| 路由 | 说明 |
|------|------|
| `/` | 登录页 |
| `/dashboard` | 控制面板 |
| `/targets` | 目标管理 |
| `/scan` | 安全扫描 |
| `/results` | 扫描结果 |

---

## 错误响应

```json
{
    "success": false,
    "message": "错误信息"
}
```

**HTTP 状态码:**
- 401: 未授权
- 404: 资源不存在
- 500: 服务器错误
