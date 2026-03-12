"""
安全基线核查平台 - 主程序入口

功能模块:
    - 用户认证与授权
    - 目标管理 (增删改查)
    - 安全扫描执行
    - 结果展示与报告下载
    - 日志记录

支持的扫描目标:
    - 操作系统: 麒麟/CentOS/Ubuntu/Windows
    - 数据库: 达梦/MySQL/Oracle

版本: v2.3.0
作者: 基线核查平台开发团队
"""
from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional, List
import os
import json
import logging

from config import settings, BASE_DIR
from models import Base, User, Target, ScanResult
from modules.auth import AuthHandler, get_current_user
from modules.logger import get_logger, setup_logger
from scanners.kylin import KylinScanner
from scanners.dameng import DamengScanner
from scanners.mysql import MySQLScanner
from scanners.oracle import OracleScanner
from scanners.windows import WindowsScanner
from scanners.linux import LinuxScanner
from scanners.apache import ApacheScanner
from scanners.nginx_scanner import NginxScanner
from scanners.redis_scanner import RedisScanner
from scanners.tomcat_scanner import TomcatScanner
from modules.report_generator import ReportGenerator
from fastapi.responses import StreamingResponse

# 初始化日志
setup_logger()
logger = get_logger("app")


# ============ 应用初始化 ============
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

# 静态文件和模板
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 数据库引擎
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

auth_handler = AuthHandler(settings.SECRET_KEY)


# ============ 数据库初始化 ============
async def init_db():
    """初始化数据库"""
    logger.info("开始初始化数据库...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表创建完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
    
    # 创建默认管理员
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.username == settings.DEFAULT_ADMIN_USER))
        if not result.scalar_one_or_none():
            admin = User(
                username=settings.DEFAULT_ADMIN_USER,
                password_hash=auth_handler.hash_password(settings.DEFAULT_ADMIN_PASS),
                is_admin=True
            )
            session.add(admin)
            await session.commit()
            logger.info(f"创建默认管理员账户: {settings.DEFAULT_ADMIN_USER}")


@app.on_event("startup")
async def startup():
    """启动事件"""
    logger.info(f"========== {settings.APP_NAME} v{settings.APP_VERSION} 启动 ==========")
    logger.info(f"数据库路径: {settings.DATABASE_URL}")
    logger.info(f"规则库目录: {settings.RULES_DIR}")
    
    await init_db()
    
    # 创建报告目录
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
    
    logger.info("服务启动完成，监听端口 8000")


# ============ 依赖注入 ============
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


# ============ 路由 - 页面 ============
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页 - 登录页"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    """控制面板"""
    try:
        user = await get_current_user(request, session, auth_handler)
    except:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "app_name": settings.APP_NAME
    })


@app.get("/targets", response_class=HTMLResponse)
async def targets_page(request: Request, session: AsyncSession = Depends(get_session)):
    """目标管理页面"""
    try:
        user = await get_current_user(request, session, auth_handler)
    except:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("targets.html", {
        "request": request,
        "user": user,
        "app_name": settings.APP_NAME
    })


@app.get("/scan", response_class=HTMLResponse)
async def scan_page(request: Request, session: AsyncSession = Depends(get_session)):
    """扫描页面"""
    try:
        user = await get_current_user(request, session, auth_handler)
    except:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("scan.html", {
        "request": request,
        "user": user,
        "app_name": settings.APP_NAME
    })


@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request, session: AsyncSession = Depends(get_session)):
    """结果查看页面"""
    try:
        user = await get_current_user(request, session, auth_handler)
    except:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("results.html", {
        "request": request,
        "user": user,
        "app_name": settings.APP_NAME
    })


# ============ API - 认证 ============
@app.post("/api/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session)
):
    """用户登录"""
    from sqlalchemy import select
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if not user or not auth_handler.verify_password(password, user.password_hash):
        logger.warning(f"登录失败 - 用户名: {username}, 原因: 用户名或密码错误")
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    token = auth_handler.create_token(user.username)
    logger.info(f"用户登录成功 - 用户名: {username}")
    
    response = JSONResponse({"success": True, "token": token})
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return response


@app.post("/api/logout")
async def logout():
    """用户登出"""
    response = JSONResponse({"success": True})
    response.delete_cookie("token")
    return response


# ============ API - 目标管理 ============
@app.get("/api/targets")
async def list_targets(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """获取目标列表"""
    try:
        await get_current_user(request, session, auth_handler)
    except:
        raise HTTPException(status_code=401, detail="未授权")
    
    from sqlalchemy import select
    result = await session.execute(select(Target))
    targets = result.scalars().all()
    
    return {
        "success": True,
        "data": [
            {
                "id": t.id,
                "name": t.name,
                "host": t.host,
                "port": t.port,
                "target_type": t.target_type,
                "username": t.username,
                "db_port": t.db_port,
                "db_username": t.db_username,
                "db_name": t.db_name,
                "scheme": t.scheme,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in targets
        ]
    }


@app.post("/api/targets")
async def create_target(
    request: Request,
    name: str = Form(...),
    host: str = Form(...),
    port: int = Form(...),
    target_type: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    # 数据库连接参数
    db_port: Optional[int] = Form(None),
    db_username: Optional[str] = Form(None),
    db_password: Optional[str] = Form(None),
    db_name: Optional[str] = Form(None),
    # Windows连接参数
    scheme: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session)
):
    """创建目标"""
    try:
        await get_current_user(request, session, auth_handler)
    except:
        raise HTTPException(status_code=401, detail="未授权")
    
    try:
        target = Target(
            name=name,
            host=host,
            port=port,
            target_type=target_type,
            username=username,
            password=password,
            db_port=db_port,
            db_username=db_username,
            db_password=db_password,
            db_name=db_name,
            scheme=scheme
        )
        session.add(target)
        await session.commit()
        
        logger.info(f"创建目标成功 - ID: {target.id}, 名称: {name}, 类型: {target_type}, 地址: {host}:{port}")
        return {"success": True, "message": "目标创建成功", "id": target.id}
    except Exception as e:
        logger.error(f"创建目标失败 - 名称: {name}, 错误: {e}")
        return {"success": False, "message": f"创建失败: {str(e)}"}


@app.put("/api/targets/{target_id}")
async def update_target(
    target_id: int,
    request: Request,
    name: str = Form(...),
    host: str = Form(...),
    port: int = Form(...),
    target_type: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    db_port: Optional[int] = Form(None),
    db_username: Optional[str] = Form(None),
    db_password: Optional[str] = Form(None),
    db_name: Optional[str] = Form(None),
    scheme: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session)
):
    """更新目标"""
    try:
        await get_current_user(request, session, auth_handler)
    except:
        raise HTTPException(status_code=401, detail="未授权")
    
    from sqlalchemy import select, update
    
    # 查找目标
    result = await session.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    
    if not target:
        logger.warning(f"更新目标失败 - ID: {target_id}, 原因: 目标不存在")
        return {"success": False, "message": "目标不存在"}
    
    # 更新目标
    target.name = name
    target.host = host
    target.port = port
    target.target_type = target_type
    target.username = username
    target.password = password
    target.db_port = db_port
    target.db_username = db_username
    target.db_password = db_password
    target.db_name = db_name
    target.scheme = scheme
    
    await session.commit()
    
    logger.info(f"更新目标成功 - ID: {target_id}, 名称: {name}")
    return {"success": True, "message": "目标更新成功"}


@app.delete("/api/targets/{target_id}")
async def delete_target(
    target_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """删除目标"""
    try:
        await get_current_user(request, session, auth_handler)
    except:
        raise HTTPException(status_code=401, detail="未授权")
    
    from sqlalchemy import delete
    await session.execute(delete(Target).where(Target.id == target_id))
    await session.commit()
    
    logger.info(f"删除目标成功 - ID: {target_id}")
    return {"success": True, "message": "目标已删除"}


# ============ API - 测试连接 ============
@app.post("/api/test-connection")
async def test_connection(
    request: Request,
    name: str = Form(default=""),
    host: str = Form(...),
    port: int = Form(...),
    target_type: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    db_port: Optional[int] = Form(None),
    db_username: Optional[str] = Form(None),
    db_password: Optional[str] = Form(None),
    db_name: Optional[str] = Form(None),
    scheme: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session)
):
    """测试目标连接"""
    try:
        await get_current_user(request, session, auth_handler)
    except:
        raise HTTPException(status_code=401, detail="未授权")
    
    logger.info(f"测试连接 - 类型: {target_type}, 主机: {host}:{port}, 用户: {username}")
    
    # 选择扫描器
    scanner_map = {
        "kylin": KylinScanner,
        "dameng": DamengScanner,
        "mysql": MySQLScanner,
        "oracle": OracleScanner,
        "windows7": WindowsScanner,
        "windows10": WindowsScanner,
        "windows2012": WindowsScanner,
        "centos": LinuxScanner,
        "ubuntu": LinuxScanner,
        "apache": ApacheScanner,
        "nginx": NginxScanner,
        "redis": RedisScanner,
        "tomcat": TomcatScanner,
    }
    
    scanner_class = scanner_map.get(target_type)
    if not scanner_class:
        return {"success": False, "message": f"不支持的类型: {target_type}"}
    
    # 创建扫描器实例
    db_types = ["dameng", "mysql", "oracle"]
    
    try:
        if target_type in db_types:
            scanner = scanner_class(
                host=host,
                port=port,
                username=username,
                password=password,
                db_port=db_port,
                db_user=db_username,
                db_password=db_password,
                db_name=db_name
            )
        else:
            scanner = scanner_class(
                host=host,
                port=port,
                username=username,
                password=password
            )
        
        # 测试连接
        connected = await scanner.connect()
        
        if connected:
            await scanner.disconnect()
            logger.info(f"测试连接成功 - 主机: {host}")
            return {"success": True, "message": f"成功连接到 {host}"}
        else:
            logger.warning(f"测试连接失败 - 主机: {host}")
            return {"success": False, "message": f"无法连接到 {host}:{port}，请检查主机地址、端口、用户名和密码"}
            
    except Exception as e:
        logger.error(f"测试连接异常 - 主机: {host}, 错误: {e}")
        return {"success": False, "message": f"连接失败: {str(e)}"}


# ============ API - 扫描 ============
@app.get("/api/rules/{target_type}")
async def get_rules(
    target_type: str,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """获取规则列表"""
    try:
        await get_current_user(request, session, auth_handler)
    except:
        raise HTTPException(status_code=401, detail="未授权")
    
    rules = []
    
    # 定义目标类型分类
    linux_types = ["kylin", "centos", "ubuntu"]
    windows_types = ["windows7", "windows10", "windows2012"]
    db_types = ["dameng", "mysql", "oracle"]
    middleware_types = ["apache", "nginx", "redis", "tomcat"]
    
    # 1. 加载该类型专属规则
    rules_dir = os.path.join(settings.RULES_DIR, target_type)
    if os.path.exists(rules_dir):
        for filename in os.listdir(rules_dir):
            if filename.endswith('.json'):
                with open(os.path.join(rules_dir, filename), 'r', encoding='utf-8') as f:
                    rule_data = json.load(f)
                    rules.append({
                        "filename": filename,
                        "name": rule_data.get("name", filename),
                        "rule_count": len(rule_data.get("rules", [])),
                        "category": "专属规则"
                    })
    
    # 2. 根据目标类型加载对应的通用规则集
    general_dir = os.path.join(settings.RULES_DIR, "general")
    
    if target_type in linux_types:
        # Linux系统 - 加载Linux信息采集规则
        linux_info_file = os.path.join(general_dir, "linux_info.json")
        if os.path.exists(linux_info_file):
            with open(linux_info_file, 'r', encoding='utf-8') as f:
                rule_data = json.load(f)
                rules.append({
                    "filename": "general/linux_info.json",
                    "name": rule_data.get("name", "Linux系统信息采集"),
                    "rule_count": len(rule_data.get("rules", [])),
                    "category": "通用规则"
                })
    
    elif target_type in windows_types:
        # Windows系统 - 加载Windows信息采集规则
        windows_info_file = os.path.join(general_dir, "windows_info.json")
        if os.path.exists(windows_info_file):
            with open(windows_info_file, 'r', encoding='utf-8') as f:
                rule_data = json.load(f)
                rules.append({
                    "filename": "general/windows_info.json",
                    "name": rule_data.get("name", "Windows系统信息采集"),
                    "rule_count": len(rule_data.get("rules", [])),
                    "category": "通用规则"
                })
    
    elif target_type in db_types:
        # 数据库 - 加载数据库信息采集规则 + GB/T 36960规则
        db_info_file = os.path.join(general_dir, "database_info.json")
        if os.path.exists(db_info_file):
            with open(db_info_file, 'r', encoding='utf-8') as f:
                rule_data = json.load(f)
                rules.append({
                    "filename": "general/database_info.json",
                    "name": rule_data.get("name", "数据库信息采集"),
                    "rule_count": len(rule_data.get("rules", [])),
                    "category": "通用规则"
                })
        
        # GB/T 36960-2018 数据库安全规则
        gbt_dir = os.path.join(settings.RULES_DIR, "gbt36960")
        if os.path.exists(gbt_dir):
            for filename in os.listdir(gbt_dir):
                if filename.endswith('.json'):
                    with open(os.path.join(gbt_dir, filename), 'r', encoding='utf-8') as f:
                        rule_data = json.load(f)
                        rules.append({
                            "filename": f"gbt36960/{filename}",
                            "name": rule_data.get("name", filename),
                            "rule_count": len(rule_data.get("rules", [])),
                            "category": "国标规则"
                        })
    
    if not rules:
        return {"success": False, "message": "未找到规则库"}
    
    return {"success": True, "data": rules}


@app.post("/api/scan")
async def start_scan(
    request: Request,
    target_id: int = Form(...),
    rule_file: str = Form(...),
    session: AsyncSession = Depends(get_session)
):
    """执行扫描"""
    try:
        await get_current_user(request, session, auth_handler)
    except:
        raise HTTPException(status_code=401, detail="未授权")
    
    logger.info(f"开始扫描任务 - 目标ID: {target_id}, 规则文件: {rule_file}")
    
    # 获取目标
    from sqlalchemy import select
    result = await session.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        logger.warning(f"扫描失败 - 目标不存在, ID: {target_id}")
        return {"success": False, "message": "目标不存在"}
    
    # 加载规则 - 支持跨目录规则文件路径（如 general/linux_info.json）
    if "/" in rule_file or "\\" in rule_file:
        # 跨目录规则文件
        rule_path = os.path.join(settings.RULES_DIR, rule_file.replace("/", os.sep).replace("\\", os.sep))
    else:
        # 原有逻辑：目标类型目录下的规则文件
        rule_path = os.path.join(settings.RULES_DIR, target.target_type, rule_file)
    
    if not os.path.exists(rule_path):
        logger.error(f"扫描失败 - 规则文件不存在: {rule_path}")
        return {"success": False, "message": f"规则文件不存在: {rule_file}"}
    
    with open(rule_path, 'r', encoding='utf-8') as f:
        rule_data = json.load(f)
    
    logger.info(f"加载规则文件: {rule_file}, 规则数: {len(rule_data.get('rules', []))}")
    
    # 选择扫描器
    scanner_map = {
        "kylin": KylinScanner,
        "dameng": DamengScanner,
        "mysql": MySQLScanner,
        "oracle": OracleScanner,
        "windows7": WindowsScanner,
        "windows10": WindowsScanner,
        "windows2012": WindowsScanner,
        "centos": LinuxScanner,
        "ubuntu": LinuxScanner,
        "general": LinuxScanner,  # 通用信息采集使用Linux扫描器
        "apache": ApacheScanner,
        "nginx": NginxScanner,
        "redis": RedisScanner,
        "tomcat": TomcatScanner,
    }
    
    scanner_class = scanner_map.get(target.target_type)
    if not scanner_class:
        logger.error(f"扫描失败 - 不支持的目标类型: {target.target_type}")
        return {"success": False, "message": f"不支持的类型: {target.target_type}"}
    
    # 执行扫描 - 根据目标类型传递不同参数
    db_types = ["dameng", "mysql", "oracle"]
    
    if target.target_type in db_types:
        # 数据库扫描器 - 传递数据库连接参数
        scanner = scanner_class(
            host=target.host,
            port=target.port,
            username=target.username,
            password=target.password,
            db_port=target.db_port,
            db_user=target.db_username,
            db_password=target.db_password,
            db_name=target.db_name
        )
        logger.info(f"创建数据库扫描器 - 类型: {target.target_type}, 主机: {target.host}, DB端口: {target.db_port}")
    else:
        # 操作系统扫描器
        scanner = scanner_class(
            host=target.host,
            port=target.port,
            username=target.username,
            password=target.password
        )
        logger.info(f"创建系统扫描器 - 类型: {target.target_type}, 主机: {target.host}:{target.port}")
    
    try:
        # 连接目标
        logger.info(f"尝试连接目标: {target.host}")
        connected = await scanner.connect()
        if not connected:
            logger.error(f"扫描失败 - 无法连接目标: {target.host}:{target.port}")
            return {"success": False, "message": f"无法连接目标 {target.host}"}
        
        # 执行扫描
        logger.info(f"开始执行扫描规则, 共 {len(rule_data.get('rules', []))} 条")
        scan_results = await scanner.scan(rule_data.get("rules", []))
        
        # 断开连接
        await scanner.disconnect()
        logger.info(f"扫描完成, 断开连接: {target.host}")
    except Exception as e:
        logger.error(f"扫描执行异常 - 目标: {target.host}, 错误: {e}")
        return {"success": False, "message": f"扫描执行失败: {str(e)}"}
    
    # 统计结果
    total = len(scan_results)
    passed = sum(1 for r in scan_results if r["status"] == "pass")
    failed = total - passed
    
    logger.info(f"扫描结果统计 - 总数: {total}, 通过: {passed}, 失败: {failed}")
    
    # 保存结果
    result_record = ScanResult(
        target_id=target.id,
        target_name=target.name,
        target_type=target.target_type,
        total_rules=total,
        passed_rules=passed,
        failed_rules=failed,
        result_data=json.dumps(scan_results, ensure_ascii=False)
    )
    session.add(result_record)
    await session.commit()
    
    logger.info(f"扫描结果已保存 - 结果ID: {result_record.id}")
    
    return {
        "success": True,
        "message": "扫描完成",
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed
        },
        "result_id": result_record.id
    }


@app.get("/api/results")
async def get_results(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """获取扫描结果列表"""
    try:
        await get_current_user(request, session, auth_handler)
    except:
        raise HTTPException(status_code=401, detail="未授权")
    
    from sqlalchemy import select
    result = await session.execute(select(ScanResult).order_by(ScanResult.scan_time.desc()))
    results = result.scalars().all()
    
    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "target_name": r.target_name,
                "target_type": r.target_type,
                "scan_time": r.scan_time.isoformat(),
                "total_rules": r.total_rules,
                "passed_rules": r.passed_rules,
                "failed_rules": r.failed_rules
            }
            for r in results
        ]
    }


@app.get("/api/results/{result_id}")
async def get_result_detail(
    result_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """获取扫描结果详情"""
    try:
        await get_current_user(request, session, auth_handler)
    except:
        raise HTTPException(status_code=401, detail="未授权")
    
    from sqlalchemy import select
    result = await session.execute(select(ScanResult).where(ScanResult.id == result_id))
    record = result.scalar_one_or_none()
    
    if not record:
        return {"success": False, "message": "结果不存在"}
    
    return {
        "success": True,
        "data": {
            "id": record.id,
            "target_name": record.target_name,
            "target_type": record.target_type,
            "scan_time": record.scan_time.isoformat(),
            "total_rules": record.total_rules,
            "passed_rules": record.passed_rules,
            "failed_rules": record.failed_rules,
            "details": json.loads(record.result_data)
        }
    }


@app.delete("/api/results/{result_id}")
async def delete_result(
    result_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """删除单个扫描结果"""
    try:
        await get_current_user(request, session, auth_handler)
    except:
        raise HTTPException(status_code=401, detail="未授权")
    
    from sqlalchemy import delete
    await session.execute(delete(ScanResult).where(ScanResult.id == result_id))
    await session.commit()
    
    logger.info(f"删除扫描结果 - ID: {result_id}")
    return {"success": True, "message": "删除成功"}


@app.post("/api/results/batch-delete")
async def batch_delete_results(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """批量删除扫描结果"""
    try:
        await get_current_user(request, session, auth_handler)
    except:
        raise HTTPException(status_code=401, detail="未授权")
    
    from sqlalchemy import delete
    import json as json_module
    
    body = await request.json()
    ids = body.get("ids", [])
    
    if not ids:
        return {"success": False, "message": "未选择要删除的结果"}
    
    result = await session.execute(delete(ScanResult).where(ScanResult.id.in_(ids)))
    await session.commit()
    
    deleted_count = result.rowcount
    logger.info(f"批量删除扫描结果 - 数量: {deleted_count}, IDs: {ids}")
    
    return {"success": True, "deleted_count": deleted_count}


# ============ API - 报告下载 ============
@app.get("/api/results/{result_id}/download")
async def download_report(
    result_id: int,
    format: str = "excel",
    request: Request = None,
    session: AsyncSession = Depends(get_session)
):
    """
    下载报告
    
    Args:
        result_id: 结果ID
        format: 报告格式 (excel/word/json)
    """
    try:
        await get_current_user(request, session, auth_handler)
    except:
        raise HTTPException(status_code=401, detail="未授权")
    
    from sqlalchemy import select
    result = await session.execute(select(ScanResult).where(ScanResult.id == result_id))
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    result_data = {
        "target_name": record.target_name,
        "target_type": record.target_type,
        "scan_time": record.scan_time.isoformat(),
        "total_rules": record.total_rules,
        "passed_rules": record.passed_rules,
        "failed_rules": record.failed_rules,
        "details": json.loads(record.result_data)
    }
    
    report_gen = ReportGenerator()
    
    if format == "excel":
        content = report_gen.generate_excel_report(result_data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"baseline_report_{result_id}.xlsx"
    elif format == "word":
        content = report_gen.generate_word_report(result_data)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"baseline_report_{result_id}.docx"
    else:
        content = json.dumps(result_data, ensure_ascii=False, indent=2).encode('utf-8')
        media_type = "application/json"
        filename = f"baseline_report_{result_id}.json"
    
    if not content:
        raise HTTPException(status_code=500, detail="报告生成失败，请检查依赖是否安装")
    
    import io
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# ============ 主程序入口 ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
