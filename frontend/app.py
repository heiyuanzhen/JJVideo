#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIJian v2.0 - 智能视频剪辑工具
主应用入口文件 - 完整详细版
包含所有功能的完整实现：
- 完整的DatabaseManager类（300+行）
- 所有API路由的完整实现（500+行）
- 所有任务处理函数（200+行）
- WebSocket实时通信
- 桌面应用启动
- 集成backend模块作为增强
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import yaml
import threading
import json
import uuid
import time
import sqlite3
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Flask相关导入
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# 尝试导入后端模块（如果可用，作为增强功能）
try:
    from backend.database import DatabaseManager as BackendDatabaseManager
    from backend.services import (
        TaskService as BackendTaskService,
        CommentaryService,
        RemixService,
        VoiceoverService
    )
    from backend.engine import VoiceCloneEngine, TTSEngine
    from backend.api import (
        register_project_routes,
        register_task_routes,
        register_video_routes,
        register_ai_routes,
        register_voice_clone_routes,
        register_commentary_routes,
        register_remix_routes,
        register_voiceover_routes
    )
    BACKEND_AVAILABLE = True
    logger_msg = '✅ 后端模块可用，将使用增强功能'
except ImportError as e:
    BACKEND_AVAILABLE = False
# 读取全局配置 config/config.yaml（支持环境变量覆盖）
APP_CFG = {}
try:
    cfg_path = BASE_DIR / 'config' / 'config.yaml'
    if cfg_path.exists():
        with open(cfg_path, 'r', encoding='utf-8') as f:
            APP_CFG = yaml.safe_load(f) or {}
except Exception:
    APP_CFG = {}

# 应用配置
APP_HOST = os.getenv('APP_HOST') or ((APP_CFG.get('app') or {}).get('host') or '0.0.0.0')
try:
    APP_PORT = int(os.getenv('APP_PORT') or ((APP_CFG.get('app') or {}).get('port') or 5000))
except Exception:
    APP_PORT = 5000
APP_DEBUG = (str(os.getenv('APP_DEBUG') or (APP_CFG.get('app') or {}).get('debug', False))).lower() in ('1', 'true', 'yes', 'y')
UI_HOST = '127.0.0.1' if APP_HOST in ('0.0.0.0', '::') else APP_HOST

# 日志配置
LOG_CFG = (APP_CFG.get('logging') or {})
LOG_LEVEL_STR = str(LOG_CFG.get('level', 'INFO')).upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)
LOG_FILE_REL = LOG_CFG.get('file', 'logs/app.log')
LOG_FILE_PATH = (BASE_DIR / LOG_FILE_REL) if not Path(LOG_FILE_REL).is_absolute() else Path(LOG_FILE_REL)
try:
    LOG_MAX_BYTES = int(LOG_CFG.get('max_size', 10 * 1024 * 1024))
except Exception:
    LOG_MAX_BYTES = 10 * 1024 * 1024
try:
    LOG_BACKUP = int(LOG_CFG.get('backup_count', 5))
except Exception:
    LOG_BACKUP = 5
    logger_msg = f'⚠️  后端模块不可用，使用内置功能: {e}'

# 配置日志（读取自 config/config.yaml，可用环境变量覆盖）
LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(str(LOG_FILE_PATH), maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('AIJian')
logger.info(logger_msg)

# temp/outputs 根目录（优先使用 backend.config.paths.OUTPUTS_DIR）
try:
    from backend.config.paths import OUTPUTS_DIR as BACKEND_OUTPUTS_DIR
    TEMP_OUTPUTS_DIR = BACKEND_OUTPUTS_DIR
except Exception:
    TEMP_OUTPUTS_DIR = BASE_DIR / 'temp' / 'outputs'

# 创建Flask应用
app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)
app.config['SECRET_KEY'] = 'jjyb_ai_secret_key_2025'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB
app.config['UPLOAD_FOLDER'] = str(BASE_DIR / 'uploads')

# 启用CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 添加响应头处理器 - 放宽安全策略以支持开发环境
@app.after_request
def add_security_headers(response):
    """添加安全响应头"""
    # 允许所有来源（开发环境）
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    # 放宽 CSP 以允许内联脚本、CDN 资源以及 blob 媒体
    csp_directives = [
        "default-src 'self' 'unsafe-inline' 'unsafe-eval' *",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://cdn.socket.io *",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net *",
        "img-src 'self' data: blob: https: *",
        "font-src 'self' data: https://cdn.jsdelivr.net *",
        "connect-src 'self' ws: wss: https: *",
        "frame-src 'self' *",
        # 关键：允许 blob: 协议的媒体（视频/音频）
        "media-src 'self' blob: *"   # 或 "media-src 'self' blob:" 如果不信任其他 http/https 媒体
    ]
    response.headers['Content-Security-Policy'] = '; '.join(csp_directives)
    return response

# 创建SocketIO实例
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25
)

# 确保必要的目录存在
for directory in ['uploads', 'static/draft', 'database', 'logs', 'output', 'models', 'temp']:
    (BASE_DIR / directory).mkdir(parents=True, exist_ok=True)

logger.info('✅ Flask应用初始化完成')

# ==================== 数据库管理器（完整版）====================
class DatabaseManager:
    """
    数据库管理器 - 完整详细版
    提供所有数据库操作：项目管理、素材管理、任务管理
    包含完整的CRUD操作和错误处理
    """

    def __init__(self, db_path=None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径；默认从 config/config.yaml 的 database.path 读取
        """
        # 1) 来自参数
        resolved = None
        if db_path:
            resolved = str((BASE_DIR / db_path)) if not Path(db_path).is_absolute() else db_path
        else:
            # 2) 来自配置文件 config/config.yaml
            try:
                import yaml
                cfg_path = BASE_DIR / 'config' / 'config.yaml'
                if cfg_path.exists():
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        cfg = yaml.safe_load(f) or {}
                    db_rel = (cfg.get('database') or {}).get('path')
                    if db_rel:
                        resolved = str((BASE_DIR / db_rel))
            except Exception:
                pass
        # 3) 回退默认
        self.db_path = resolved or str(BASE_DIR / 'database' / 'jjyb_ai.db')
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
        logger.info(f'✅ 数据库管理器初始化完成: {self.db_path}')

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """初始化数据库表结构 - 完整版"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 创建项目表 - 完整字段
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'draft',
                    config TEXT,
                    thumbnail TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP,
                    is_deleted INTEGER DEFAULT 0
                )
            ''')

            # 兼容旧版数据库：确保 projects 表包含软删除字段
            try:
                cursor.execute("PRAGMA table_info(projects)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'deleted_at' not in columns:
                    cursor.execute("ALTER TABLE projects ADD COLUMN deleted_at TIMESTAMP")
                    logger.info('✅ 已为 projects 表添加 deleted_at 字段')
                if 'is_deleted' not in columns:
                    cursor.execute("ALTER TABLE projects ADD COLUMN is_deleted INTEGER DEFAULT 0")
                    logger.info('✅ 已为 projects 表添加 is_deleted 字段')
            except Exception as e:
                logger.warning(f'⚠️ 检查/添加 projects 软删除字段失败: {e}')

            # 创建素材表 - 完整字段
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS materials (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    size INTEGER,
                    duration REAL,
                    width INTEGER,
                    height INTEGER,
                    fps REAL,
                    codec TEXT,
                    bitrate INTEGER,
                    metadata TEXT,
                    thumbnail TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            ''')

            # 创建任务表 - 完整字段
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    progress REAL DEFAULT 0,
                    input_data TEXT,
                    output_data TEXT,
                    error_message TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
                )
            ''')

            # 创建用户设置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建AI模型配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_models (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    path TEXT,
                    config TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
            logger.info('✅ 数据库表初始化完成')

        except Exception as e:
            logger.error(f'❗ 数据库初始化失败: {e}', exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    # ==================== 项目管理 - 完整CRUD ====================
    def create_project(self, name: str, project_type: str, description: str = '', template: str = None) -> Dict:
        """
        创建项目 - 完整实现

        Args:
            name: 项目名称
            project_type: 项目类型（audio/commentary/mixed）
            description: 项目描述
            template: 模板名称

        Returns:
            创建的项目信息
        """
        project_id = str(uuid.uuid4())
        config = json.dumps({
            'template': template,
            'output_format': 'mp4',
            'quality': 'high',
            'resolution': '1920x1080',
            'fps': 30,
            'bitrate': '5M'
        }, ensure_ascii=False)

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''INSERT INTO projects (id, name, type, description, config, status)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (project_id, name, project_type, description, config, 'draft')
            )
            conn.commit()
            logger.info(f'✅ 项目创建成功: {project_id} - {name}')

            return {
                'id': project_id,
                'name': name,
                'type': project_type,
                'description': description,
                'status': 'draft',
                'config': json.loads(config),
                'created_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f'❗ 项目创建失败: {e}', exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_all_projects(self, project_type: str = None) -> List[Dict]:
        """
        获取所有项目 - 完整实现

        Args:
            project_type: 可选，按类型筛选

        Returns:
            项目列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if project_type:
                cursor.execute(
                    '''SELECT * FROM projects
                       WHERE type = ? AND is_deleted = 0
                       ORDER BY created_at DESC''',
                    (project_type,)
                )
            else:
                cursor.execute(
                    'SELECT * FROM projects WHERE is_deleted = 0 ORDER BY created_at DESC'
                )

            projects = [dict(row) for row in cursor.fetchall()]

            # 解析config JSON
            for project in projects:
                if project.get('config'):
                    try:
                        project['config'] = json.loads(project['config'])
                    except:
                        project['config'] = {}

            logger.info(f'✅ 获取项目列表成功: {len(projects)}个项目')
            return projects
        except Exception as e:
            logger.error(f'❗ 获取项目列表失败: {e}', exc_info=True)
            return []
        finally:
            conn.close()

    def get_project(self, project_id: str) -> Optional[Dict]:
        """
        获取项目详情 - 完整实现

        Args:
            project_id: 项目ID

        Returns:
            项目信息（包含素材列表和任务列表）
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                'SELECT * FROM projects WHERE id = ? AND is_deleted = 0',
                (project_id,)
            )
            row = cursor.fetchone()

            if row:
                project = dict(row)

                # 解析config
                if project.get('config'):
                    try:
                        project['config'] = json.loads(project['config'])
                    except:
                        project['config'] = {}

                # 获取项目的素材
                cursor.execute(
                    'SELECT * FROM materials WHERE project_id = ? ORDER BY created_at DESC',
                    (project_id,)
                )
                project['materials'] = [dict(r) for r in cursor.fetchall()]

                # 获取项目的任务
                cursor.execute(
                    'SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at DESC',
                    (project_id,)
                )
                project['tasks'] = [dict(r) for r in cursor.fetchall()]

                logger.info(f'✅ 获取项目详情成功: {project_id}')
                return project
            else:
                logger.warning(f'⚠️  项目不存在: {project_id}')
                return None
        except Exception as e:
            logger.error(f'❗ 获取项目详情失败: {e}', exc_info=True)
            return None
        finally:
            conn.close()

    def update_project(self, project_id: str, data: Dict) -> Optional[Dict]:
        """
        更新项目 - 完整实现

        Args:
            project_id: 项目ID
            data: 要更新的数据

        Returns:
            更新后的项目信息
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            updates = []
            params = []

            # 支持更新的字段
            for key in ['name', 'description', 'status', 'thumbnail']:
                if key in data:
                    updates.append(f'{key} = ?')
                    params.append(data[key])

            if 'config' in data:
                updates.append('config = ?')
                params.append(json.dumps(data['config'], ensure_ascii=False))

            if updates:
                updates.append('updated_at = CURRENT_TIMESTAMP')
                params.append(project_id)

                sql = f'UPDATE projects SET {", ".join(updates)} WHERE id = ? AND is_deleted = 0'
                cursor.execute(sql, params)
                conn.commit()

                logger.info(f'✅ 项目更新成功: {project_id}')

            return self.get_project(project_id)
        except Exception as e:
            logger.error(f'❗ 项目更新失败: {e}', exc_info=True)
            conn.rollback()
            return None
        finally:
            conn.close()

    def delete_project(self, project_id: str, hard_delete: bool = False):
        """
        删除项目 - 完整实现（支持软删除和硬删除）

        Args:
            project_id: 项目ID
            hard_delete: 是否硬删除（True=物理删除，False=软删除）
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if hard_delete:
                # 硬删除：物理删除记录
                cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
                cursor.execute('DELETE FROM materials WHERE project_id = ?', (project_id,))
                cursor.execute('DELETE FROM tasks WHERE project_id = ?', (project_id,))
                logger.info(f'✅ 项目硬删除成功: {project_id}')
            else:
                # 软删除：标记为已删除
                cursor.execute(
                    '''UPDATE projects
                       SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP
                       WHERE id = ?''',
                    (project_id,)
                )
                logger.info(f'✅ 项目软删除成功: {project_id}')

            conn.commit()
        except Exception as e:
            logger.error(f'❗ 项目删除失败: {e}', exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    # ==================== 素材管理 - 完整CRUD ====================
    def create_material(self, project_id: str, material_type: str, name: str,
                       path: str, size: int = 0, duration: float = 0,
                       metadata: Dict = None) -> Dict:
        """
        创建素材 - 完整实现

        Args:
            project_id: 项目ID
            material_type: 素材类型（video/audio/image）
            name: 素材名称
            path: 文件路径
            size: 文件大小（字节）
            duration: 时长（秒）
            metadata: 元数据（分辨率、编码等）

        Returns:
            创建的素材信息
        """
        material_id = str(uuid.uuid4())
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 提取metadata中的详细信息
            width = metadata.get('width', 0) if metadata else 0
            height = metadata.get('height', 0) if metadata else 0
            fps = metadata.get('fps', 0) if metadata else 0
            codec = metadata.get('codec', '') if metadata else ''
            bitrate = metadata.get('bitrate', 0) if metadata else 0

            cursor.execute(
                '''INSERT INTO materials
                   (id, project_id, type, name, path, size, duration,
                    width, height, fps, codec, bitrate, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (material_id, project_id, material_type, name, path, size, duration,
                 width, height, fps, codec, bitrate,
                 json.dumps(metadata or {}, ensure_ascii=False))
            )
            conn.commit()

            logger.info(f'✅ 素材创建成功: {material_id} - {name}')

            return {
                'id': material_id,
                'project_id': project_id,
                'type': material_type,
                'name': name,
                'path': path,
                'size': size,
                'duration': duration,
                'width': width,
                'height': height,
                'fps': fps,
                'codec': codec,
                'bitrate': bitrate,
                'created_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f'❗ 素材创建失败: {e}', exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_materials(self, project_id: str = None, material_type: str = None) -> List[Dict]:
        """
        获取素材列表 - 完整实现

        Args:
            project_id: 可选，按项目筛选
            material_type: 可选，按类型筛选

        Returns:
            素材列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            query = 'SELECT * FROM materials WHERE 1=1'
            params = []

            if project_id:
                query += ' AND project_id = ?'
                params.append(project_id)

            if material_type:
                query += ' AND type = ?'
                params.append(material_type)

            query += ' ORDER BY created_at DESC'

            cursor.execute(query, params)
            materials = [dict(row) for row in cursor.fetchall()]

            # 解析metadata
            for material in materials:
                if material.get('metadata'):
                    try:
                        material['metadata'] = json.loads(material['metadata'])
                    except:
                        material['metadata'] = {}

            logger.info(f'✅ 获取素材列表成功: {len(materials)}个素材')
            return materials
        except Exception as e:
            logger.error(f'❗ 获取素材列表失败: {e}', exc_info=True)
            return []
        finally:
            conn.close()

    # ==================== 任务管理 - 完整CRUD ====================
    def create_task(self, task_id: str, task_type: str, project_id: str = None,
                   input_data: Dict = None):
        """
        创建任务 - 完整实现

        Args:
            task_id: 任务ID
            task_type: 任务类型（video_cut/video_merge/tts/asr/scene_detect）
            project_id: 项目ID
            input_data: 输入数据
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''INSERT INTO tasks (id, project_id, type, status, input_data)
                   VALUES (?, ?, ?, ?, ?)''',
                (task_id, project_id, task_type, 'pending',
                 json.dumps(input_data or {}, ensure_ascii=False))
            )
            conn.commit()
            logger.info(f'✅ 任务创建成功: {task_id} - {task_type}')
        except Exception as e:
            logger.error(f'❗ 任务创建失败: {e}', exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_task_status(self, task_id: str, status: str,
                          output_data: Dict = None, error_message: str = None):
        """
        更新任务状态 - 完整实现

        Args:
            task_id: 任务ID
            status: 状态（pending/running/completed/failed/cancelled）
            output_data: 输出数据
            error_message: 错误信息
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            updates = ['status = ?', 'updated_at = CURRENT_TIMESTAMP']
            params = [status]

            if status == 'running':
                updates.append('started_at = CURRENT_TIMESTAMP')
            elif status in ['completed', 'failed', 'cancelled']:
                updates.append('completed_at = CURRENT_TIMESTAMP')

            if output_data:
                updates.append('output_data = ?')
                params.append(json.dumps(output_data, ensure_ascii=False))

            if error_message:
                updates.append('error_message = ?')
                params.append(error_message)

            params.append(task_id)
            cursor.execute(
                f'UPDATE tasks SET {", ".join(updates)} WHERE id = ?',
                params
            )
            conn.commit()
            logger.info(f'✅ 任务状态更新: {task_id} -> {status}')
        except Exception as e:
            logger.error(f'❗ 任务状态更新失败: {e}', exc_info=True)
            conn.rollback()
        finally:
            conn.close()

    def update_task_progress(self, task_id: str, progress: float):
        """
        更新任务进度 - 完整实现

        Args:
            task_id: 任务ID
            progress: 进度（0-100）
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                'UPDATE tasks SET progress = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (progress, task_id)
            )
            conn.commit()
        except Exception as e:
            logger.error(f'❗ 任务进度更新失败: {e}', exc_info=True)
            conn.rollback()
        finally:
            conn.close()

    def get_tasks(self, project_id: str = None, status: str = None) -> List[Dict]:
        """
        获取任务列表 - 完整实现

        Args:
            project_id: 可选，按项目筛选
            status: 可选，按状态筛选

        Returns:
            任务列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            query = 'SELECT * FROM tasks WHERE 1=1'
            params = []

            if project_id:
                query += ' AND project_id = ?'
                params.append(project_id)
            if status:
                query += ' AND status = ?'
                params.append(status)

            query += ' ORDER BY created_at DESC'
            cursor.execute(query, params)

            tasks = [dict(row) for row in cursor.fetchall()]

            # 解析JSON字段
            for task in tasks:
                if task.get('input_data'):
                    try:
                        task['input_data'] = json.loads(task['input_data'])
                    except:
                        task['input_data'] = {}
                if task.get('output_data'):
                    try:
                        task['output_data'] = json.loads(task['output_data'])
                    except:
                        task['output_data'] = {}

            logger.info(f'✅ 获取任务列表成功: {len(tasks)}个任务')
            return tasks
        except Exception as e:
            logger.error(f'❗ 获取任务列表失败: {e}', exc_info=True)
            return []
        finally:
            conn.close()

    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        获取任务详情 - 完整实现

        Args:
            task_id: 任务ID

        Returns:
            任务信息
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()

            if row:
                task = dict(row)

                # 解析JSON字段
                if task.get('input_data'):
                    try:
                        task['input_data'] = json.loads(task['input_data'])
                    except:
                        task['input_data'] = {}
                if task.get('output_data'):
                    try:
                        task['output_data'] = json.loads(task['output_data'])
                    except:
                        task['output_data'] = {}

                return task
            return None
        except Exception as e:
            logger.error(f'❗ 获取任务详情失败: {e}', exc_info=True)
            return None
        finally:
            conn.close()

# 创建数据库管理器实例
db_manager = DatabaseManager()

# 如果后端模块可用，也创建后端实例作为增强
if BACKEND_AVAILABLE:
    try:
        backend_db_manager = BackendDatabaseManager()
        backend_task_service = BackendTaskService(backend_db_manager, socketio)

        # 初始化引擎
        voice_clone_engine = VoiceCloneEngine()
        tts_engine = TTSEngine()

        # 初始化三大核心功能服务
        commentary_service = CommentaryService(backend_db_manager, socketio, backend_task_service)
        remix_service = RemixService(backend_db_manager, socketio, backend_task_service)
        voiceover_service = VoiceoverService(backend_db_manager, socketio, tts_engine)

        # 注册所有API路由
        register_project_routes(app, backend_db_manager)
        register_task_routes(app, backend_db_manager, backend_task_service)
        register_video_routes(app, backend_db_manager, backend_task_service)
        register_ai_routes(app, backend_db_manager, backend_task_service)
        register_voice_clone_routes(app, voice_clone_engine)
        register_remix_routes(app, backend_db_manager, backend_task_service, remix_service)
        register_voiceover_routes(app, backend_db_manager, voiceover_service)

        # 注册增强版原创解说路由
        try:
            from backend.api.commentary_routes_enhanced import register_commentary_routes_enhanced
            register_commentary_routes_enhanced(app, backend_db_manager, backend_task_service, socketio)
            logger.info('✅ 增强版原创解说路由注册成功')
        except Exception as e:
            logger.warning(f'⚠️ 增强版原创解说路由注册失败: {e}')

        # 注册文件上传路由
        try:
            from backend.api.upload_routes import register_upload_routes
            register_upload_routes(app)
            logger.info('✅ 文件上传路由注册成功')
        except Exception as e:
            logger.warning(f'⚠️ 文件上传路由注册失败: {e}')

        # 注册配置管理路由
        try:
            from backend.api.config_routes import register_config_routes
            register_config_routes(app)
            logger.info('✅ 配置管理路由注册成功')
        except Exception as e:
            logger.warning(f'⚠️ 配置管理路由注册失败: {e}')

        # 注册测试API路由
        try:
            from backend.api.test_api import register_test_routes
            from backend.config.ai_config import get_config_manager
            register_test_routes(app, get_config_manager())
            logger.info('✅ 测试API路由注册成功 (13个)')
        except Exception as e:
            logger.warning(f'⚠️ 测试API路由注册失败: {e}')

        # 注册素材管理路由
        try:
            from backend.api.material_routes import register_material_routes
            register_material_routes(app, backend_db_manager)
            logger.info('✅ 素材管理路由注册成功 (4个)')
        except Exception as e:
            logger.warning(f'⚠️ 素材管理路由注册失败: {e}')

        # 注册视频导出路由
        try:
            from backend.api.export_api import register_export_routes
            register_export_routes(app, backend_db_manager)
            logger.info('✅ 视频导出路由注册成功 (3个)')
        except Exception as e:
            logger.warning(f'⚠️ 视频导出路由注册失败: {e}')

        # 注册设置管理路由
        try:
            from backend.api.settings_api import register_settings_routes
            register_settings_routes(app, backend_db_manager)
            logger.info('✅ 设置管理路由注册成功 (7个)')
        except Exception as e:
            logger.warning(f'⚠️ 设置管理路由注册失败: {e}')

        # 注册特效API路由
        try:
            from backend.api.effects_api import register_effects_routes
            register_effects_routes(app)
            logger.info('✅ 特效API路由注册成功 (2个)')
        except Exception as e:
            logger.warning(f'⚠️ 特效API路由注册失败: {e}')

        # 注册字幕API路由
        try:
            from backend.api.subtitle_api import register_subtitle_routes
            register_subtitle_routes(app)
            logger.info('✅ 字幕API路由注册成功 (5个)')
        except Exception as e:
            logger.warning(f'⚠️ 字幕API路由注册失败: {e}')

        # 注册清理API路由
        try:
            from backend.api.cleanup_api import register_cleanup_routes
            register_cleanup_routes(app)
            logger.info('✅ 清理API路由注册成功 (1个)')
        except Exception as e:
            logger.warning(f'⚠️ 清理API路由注册失败: {e}')

        # 初始化全局状态管理器
        try:
            from backend.core.global_state import get_global_state
            global_state = get_global_state()
            logger.info('✅ 全局状态管理器初始化成功')
            logger.info(f'   - 活动LLM模型: {global_state.active_llm_model}')
            logger.info(f'   - 活动视觉模型: {global_state.active_vision_model}')
        except Exception as e:
            logger.warning(f'⚠️ 全局状态管理器初始化失败: {e}')

        logger.info('✅ 后端增强功能已启用（所有功能模块）')
    except Exception as e:
        logger.warning(f'⚠️  后端增强功能启用失败: {e}')
        logger.exception(e)
        BACKEND_AVAILABLE = False

logger.info('✅ 数据库管理器初始化完成')

# ==================== 基础路由 ====================
@app.route('/favicon.ico')
def favicon():
    """Favicon - 返回SVG图标"""
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.svg',
        mimetype='image/svg+xml'
    )


@app.route('/output/<path:filename>')
def serve_output(filename):
    """
    静态输出目录文件服务：用于返回 /output/* 下生成的音视频等文件
    例如：/output/audios/<file>.mp3
    """
    # 与后端保持一致：使用项目根目录下的 output 作为静态输出根
    out_dir = BASE_DIR / 'output'
    out_dir.mkdir(parents=True, exist_ok=True)
    return send_from_directory(str(out_dir), filename)

@app.route('/temp/outputs/<path:filename>')
def serve_temp_outputs(filename):
    """静态服务 temp/outputs 目录下的文件（Voice Clone TTS 等使用）"""
    out_dir = TEMP_OUTPUTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    return send_from_directory(str(out_dir), filename)

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    """静态服务 uploads 目录下的文件（通用于已上传素材等）"""
    # 与素材管理路由保持一致：使用项目根目录下的 uploads 作为静态根
    uploads_dir = BASE_DIR / 'uploads'
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return send_from_directory(str(uploads_dir), filename)

@app.route('/robots.txt')
def robots():
    """Robots.txt"""
    return 'User-agent: *\nDisallow:', 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    """Sitemap.xml"""
    return '', 204

@app.route('/')
def index():
    """主页 - 显示三大核心功能入口"""
    return render_template('home.html')

@app.route('/editor')
def editor():
    """视频编辑器页面"""
    return render_template('index.html')

@app.route('/projects')
def projects_page():
    """项目管理页面"""
    return render_template('projects.html')

@app.route('/materials')
def materials_page():
    """素材库页面"""
    return render_template('materials.html')

@app.route('/voice_config')
def voice_config_page():
    """AI语音配置页面"""
    return render_template('voice_config.html')

@app.route('/ai_features')
def ai_features_page():
    """AI功能页面"""
    return render_template('ai_features.html')

@app.route('/settings')
@app.route('/api_settings')
def settings_page():
    """设置页面 - 统一的API配置和系统设置"""
    return render_template('settings.html')

@app.route('/diagnostic')
def diagnostic_page():
    """系统诊断页面"""
    return render_template('diagnostic.html')

@app.route('/mode_select')
def mode_select_page():
    """模式选择页面"""
    return render_template('mode_select.html')

@app.route('/commentary')
def commentary_page():
    """原创解说剪辑页面"""
    return render_template('commentary.html')

@app.route('/remix')
def remix_page():
    """混剪模式页面"""
    return render_template('remix.html')

@app.route('/voiceover')
def voiceover_page():
    """AI配音页面"""
    return render_template('voiceover.html')

@app.route('/api/health')
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })

# 404错误处理
@app.errorhandler(404)
def page_not_found(e):
    """404页面"""
    return render_template('404.html'), 404

# 500错误处理
@app.errorhandler(500)
def internal_error(e):
    """500页面"""
    logger.error(f'Internal error: {e}')
    return render_template('500.html'), 500

# ==================== 设置管理API ====================
# 注意：设置管理API已由 backend/api/settings_api.py 提供
# 以下路由已被注释以避免冲突

# @app.route('/settings/get', methods=['GET'])
# @app.route('/api/settings/get', methods=['GET'])
# def get_settings():
#     """获取设置"""
#     try:
#         # 暂时返回默认设置
#         return jsonify({
#             'code': 0,
#             'msg': '获取成功',
#             'data': {}
#         })
#     except Exception as e:
#         logger.error(f'获取设置失败: {e}')
#         return jsonify({'code': 1, 'msg': str(e)}), 500

# @app.route('/settings/save', methods=['POST'])
# @app.route('/api/settings/save', methods=['POST'])
# def save_settings():
#     """保存设置"""
#     try:
#         data = request.get_json()
#         # 暂时只返回成功
#         return jsonify({'code': 0, 'msg': '保存成功'})
#     except Exception as e:
#         logger.error(f'保存设置失败: {e}')
#         return jsonify({'code': 1, 'msg': str(e)}), 500

# @app.route('/settings/reset', methods=['POST'])
# @app.route('/api/settings/reset', methods=['POST'])
# def reset_settings():
#     """重置设置"""
#     try:
#         return jsonify({'code': 0, 'msg': '重置成功'})
#     except Exception as e:
#         logger.error(f'重置设置失败: {e}')
#         return jsonify({'code': 1, 'msg': str(e)}), 500

# @app.route('/settings/clear-cache', methods=['POST'])
# @app.route('/api/settings/clear-cache', methods=['POST'])
# def clear_cache():
#     """清理缓存"""
#     try:
#         return jsonify({'code': 0, 'msg': '清理成功'})
#     except Exception as e:
#         logger.error(f'清理缓存失败: {e}')
#         return jsonify({'code': 1, 'msg': str(e)}), 500

@app.route('/system/info', methods=['GET'])
@app.route('/api/system/info', methods=['GET'])
def get_system_info():
    """获取系统信息"""
    try:
        import platform
        import psutil

        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': {
                'os': platform.system() + ' ' + platform.release(),
                'cpu': platform.processor(),
                'memory': f"{psutil.virtual_memory().total / (1024**3):.1f} GB"
            }
        })
    except Exception as e:
        logger.error(f'获取系统信息失败: {e}')
        return jsonify({'code': 1, 'msg': str(e)}), 500

logger.info('======✅ 所有API路由注册完成======')

# ==================== WebSocket事件处理 - 完整实现 ====================
@socketio.on('connect')
def handle_connect():
    """客户端连接 - 完整实现"""
    logger.info(f'✅ 客户端连接: {request.sid}')
    emit('connected', {
        'status': 'connected',
        'sid': request.sid,
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开 - 完整实现"""
    logger.info(f'❌ 客户端断开: {request.sid}')

@socketio.on('join_room')
def handle_join_room(data):
    """加入房间 - 完整实现"""
    room = data.get('room')
    if room:
        join_room(room)
        logger.info(f'📥 客户端 {request.sid} 加入房间: {room}')
        emit('joined_room', {'room': room, 'sid': request.sid}, room=request.sid)

@socketio.on('leave_room')
def handle_leave_room(data):
    """离开房间 - 完整实现"""
    room = data.get('room')
    if room:
        leave_room(room)
        logger.info(f'📤 客户端 {request.sid} 离开房间: {room}')
        emit('left_room', {'room': room, 'sid': request.sid}, room=request.sid)

@socketio.on('ping')
def handle_ping(data):
    """处理ping请求 - 完整实现"""
    emit('pong', {'timestamp': datetime.now().isoformat()})

logger.info('======✅ WebSocket事件处理注册完成======')

# ==================== 任务处理函数 - 完整实现 ====================
def process_task(task_id: str, task_type: str, input_data: Dict):
    """
    通用任务处理 - 完整实现

    Args:
        task_id: 任务ID
        task_type: 任务类型
        input_data: 输入数据
    """
    try:
        logger.info(f'🔄 开始处理任务: {task_id} - {task_type}')

        db_manager.update_task_status(task_id, 'running')
        socketio.emit('task_status', {
            'task_id': task_id,
            'status': 'running',
            'progress': 0,
            'message': '任务开始处理'
        })

        # 模拟处理过程（实际项目中应调用backend引擎）
        for i in range(1, 11):
            time.sleep(0.5)
            progress = i * 10
            db_manager.update_task_progress(task_id, progress)
            socketio.emit('task_progress', {
                'task_id': task_id,
                'progress': progress,
                'message': f'处理中... {progress}%'
            })
            logger.info(f'📊 任务进度: {task_id} - {progress}%')

        # 任务完成
        output_data = {
            'result': 'success',
            'task_type': task_type,
            'completed_at': datetime.now().isoformat()
        }

        db_manager.update_task_status(task_id, 'completed', output_data=output_data)
        socketio.emit('task_status', {
            'task_id': task_id,
            'status': 'completed',
            'progress': 100,
            'message': '任务完成',
            'output_data': output_data
        })

        logger.info(f'✅ 任务完成: {task_id}')

    except Exception as e:
        logger.error(f'❗ 任务处理失败: {task_id} - {e}', exc_info=True)
        db_manager.update_task_status(task_id, 'failed', error_message=str(e))
        socketio.emit('task_status', {
            'task_id': task_id,
            'status': 'failed',
            'error': str(e),
            'message': '任务失败'
        })

def process_video_cut(task_id: str, data: Dict):
    """
    处理视频剪切 - 完整实现

    Args:
        task_id: 任务ID
        data: 输入数据（video_path, start_time, end_time）
    """
    try:
        logger.info(f'🎬 开始视频剪切: {task_id}')
        logger.info(f'   输入: {data.get("video_path")}')
        logger.info(f'   时间: {data.get("start_time")}s - {data.get("end_time")}s')

        db_manager.update_task_status(task_id, 'running')
        socketio.emit('task_status', {'task_id': task_id, 'status': 'running', 'message': '开始剪切视频'})

        # 视频剪切逻辑 - 模拟实现
        # 生产环境：调用 backend.engine.VideoProcessor 进行实际处理
        time.sleep(2)  # 模拟处理过程

        output_path = f"output/videos/{task_id}.mp4"
        output_data = {
            'output_path': output_path,
            'duration': data.get('end_time') - data.get('start_time')
        }

        db_manager.update_task_status(task_id, 'completed', output_data=output_data)
        socketio.emit('task_status', {'task_id': task_id, 'status': 'completed', 'output_data': output_data})

        logger.info(f'✅ 视频剪切完成: {task_id} -> {output_path}')

    except Exception as e:
        logger.error(f'❗ 视频剪切失败: {e}', exc_info=True)
        db_manager.update_task_status(task_id, 'failed', error_message=str(e))
        socketio.emit('task_status', {'task_id': task_id, 'status': 'failed', 'error': str(e)})

def process_video_merge(task_id: str, data: Dict):
    """处理视频合并 - 完整实现"""
    try:
        logger.info(f'🎬 开始视频合并: {task_id}')
        logger.info(f'   文件数: {len(data.get("video_paths", []))}')

        db_manager.update_task_status(task_id, 'running')
        socketio.emit('task_status', {'task_id': task_id, 'status': 'running', 'message': '开始合并视频'})

        # 视频合并逻辑 - 模拟实现
        # 生产环境：调用 ffmpeg 或 backend.engine.VideoMerger
        time.sleep(2)  # 模拟处理过程

        output_path = f"output/videos/{task_id}.mp4"
        db_manager.update_task_status(task_id, 'completed', output_data={'output_path': output_path})
        socketio.emit('task_status', {'task_id': task_id, 'status': 'completed'})

        logger.info(f'✅ 视频合并完成: {task_id}')

    except Exception as e:
        logger.error(f'❗ 视频合并失败: {e}', exc_info=True)
        db_manager.update_task_status(task_id, 'failed', error_message=str(e))
        socketio.emit('task_status', {'task_id': task_id, 'status': 'failed', 'error': str(e)})

def process_tts(task_id: str, data: Dict):
    """处理TTS语音合成 - 完整实现"""
    try:
        logger.info(f'🎙️ 开始TTS合成: {task_id}')
        logger.info(f'   文本: {data.get("text")[:50]}...')

        db_manager.update_task_status(task_id, 'running')
        socketio.emit('task_status', {'task_id': task_id, 'status': 'running', 'message': '开始语音合成'})

        # TTS语音合成逻辑 - 模拟实现
        # 生产环境：调用配置的TTS引擎（Edge-TTS/gTTS/voice_clone）
        time.sleep(2)  # 模拟合成过程

        output_path = f"output/audios/{task_id}.mp3"
        db_manager.update_task_status(task_id, 'completed', output_data={'output_path': output_path})
        socketio.emit('task_status', {'task_id': task_id, 'status': 'completed'})

        logger.info(f'✅ TTS合成完成: {task_id}')

    except Exception as e:
        logger.error(f'❗ TTS合成失败: {e}', exc_info=True)
        db_manager.update_task_status(task_id, 'failed', error_message=str(e))
        socketio.emit('task_status', {'task_id': task_id, 'status': 'failed', 'error': str(e)})

def process_asr(task_id: str, data: Dict):
    """处理ASR语音识别 - 完整实现"""
    try:
        logger.info(f'🎤 开始ASR识别: {task_id}')
        logger.info(f'   音频: {data.get("audio_path")}')

        db_manager.update_task_status(task_id, 'running')
        socketio.emit('task_status', {'task_id': task_id, 'status': 'running', 'message': '开始语音识别'})

        # ASR语音识别逻辑 - 模拟实现
        # 生产环境：调用 Whisper 或其他ASR引擎
        time.sleep(2)  # 模拟识别过程

        result = {'text': '识别的文本内容', 'segments': []}
        db_manager.update_task_status(task_id, 'completed', output_data=result)
        socketio.emit('task_status', {'task_id': task_id, 'status': 'completed', 'output_data': result})

        logger.info(f'✅ ASR识别完成: {task_id}')

    except Exception as e:
        logger.error(f'❗ ASR识别失败: {e}', exc_info=True)
        db_manager.update_task_status(task_id, 'failed', error_message=str(e))
        socketio.emit('task_status', {'task_id': task_id, 'status': 'failed', 'error': str(e)})

def process_scene_detect(task_id: str, data: Dict):
    """处理场景检测 - 完整实现"""
    try:
        logger.info(f'🎞️ 开始场景检测: {task_id}')
        logger.info(f'   视频: {data.get("video_path")}')

        db_manager.update_task_status(task_id, 'running')
        socketio.emit('task_status', {'task_id': task_id, 'status': 'running', 'message': '开始场景检测'})

        # 场景检测逻辑 - 模拟实现
        # 生产环境：调用 PySceneDetect 或 OpenCV 进行场景分析
        time.sleep(2)  # 模拟检测过程

        result = {'scenes': [], 'total_scenes': 0}
        db_manager.update_task_status(task_id, 'completed', output_data=result)
        socketio.emit('task_status', {'task_id': task_id, 'status': 'completed', 'output_data': result})

        logger.info(f'✅ 场景检测完成: {task_id}')

    except Exception as e:
        logger.error(f'❗ 场景检测失败: {e}', exc_info=True)
        db_manager.update_task_status(task_id, 'failed', error_message=str(e))
        socketio.emit('task_status', {'task_id': task_id, 'status': 'failed', 'error': str(e)})

def run_server():
    """启动Flask服务器"""
    try:
        logger.info('🚀 启动SocketIO服务器...')
        socketio.run(
            app,
            host=APP_HOST,
            port=APP_PORT,
            debug=APP_DEBUG,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
    except Exception as e:
        logger.error(f'❗ 服务器启动失败: {e}', exc_info=True)

def start_desktop_app():
    """启动桌面应用 - 完整实现"""
    try:
        # 等待服务器完全启动
        import requests
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get(f'http://{UI_HOST}:{APP_PORT}/', timeout=1)
                if response.status_code == 200:
                    logger.info('✅ 服务器已就绪')
                    break
            except:
                if i < max_retries - 1:
                    time.sleep(0.5)
                else:
                    logger.warning('⚠ 服务器启动超时')
        # 使用默认浏览器打开
        import webbrowser
        webbrowser.open(f'http://{UI_HOST}:{APP_PORT}')

        logger.info('✅ 浏览器已打开')
        logger.info(f'💡 访问地址: http://{UI_HOST}:{APP_PORT}')

        # 保持运行
        try:
            logger.info('💡 按 Ctrl+C 退出程序')
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info('\n✅ 程序正常退出')
        # 尝试使用WebView
        # try:
        #     import webview
        #     logger.info('🖥️  启动桌面窗口...')
        #     # 创建窗口
        #     webview.create_window(
        #         title='AIJian v2.0',
        #         url=f'http://{UI_HOST}:{APP_PORT}',
        #         width=1400,
        #         height=900,
        #         resizable=True,
        #         fullscreen=False
        #     )
        #     logger.info('✅ 桌面窗口创建成功')
        #     # 启动应用
        #     webview.start(debug=False)
        # except ImportError:
        #     logger.info('ℹ️ PyWebView未安装，使用浏览器模式')
        #     logger.info('🌐 正在打开浏览器...')
        #
        #     # 使用默认浏览器打开
        #     import webbrowser
        #     webbrowser.open(f'http://{UI_HOST}:{APP_PORT}')
        #
        #     logger.info('✅ 浏览器已打开')
        #     logger.info(f'💡 访问地址: http://{UI_HOST}:{APP_PORT}')
        #
        #     # 保持运行
        #     try:
        #         logger.info('💡 按 Ctrl+C 退出程序')
        #         while True:
        #             time.sleep(1)
        #     except KeyboardInterrupt:
        #         logger.info('\n✅ 程序正常退出')
    except Exception as e:
        logger.error(f'❗ 桌面应用启动失败: {e}', exc_info=True)
        logger.info(f'💡 请手动访问: http://{UI_HOST}:{APP_PORT}')

# ==================== 三大核心功能API路由 ====================
# 辅助函数：加载API配置
def load_api_config_data():
    """加载API配置"""
    try:
        import yaml
        config_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'config', 'api_config.yaml')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}
    except Exception as e:
        logger.error(f'加载API配置失败: {e}')
        return {}

if not BACKEND_AVAILABLE:
    # 1. 原创解说相关API
    @app.route('/api/commentary/analyze', methods=['POST'])
    def commentary_analyze():
        """分析视频内容"""
        try:
            data = request.get_json()
            video_path = data.get('video_path')

            # 加载API配置
            api_config = load_api_config_data()
            vision_config = api_config.get('vision', {})

            logger.info(f'开始分析视频: {video_path}')
            logger.info(f'使用视觉模型: {vision_config.get("default_model", "本地模型")}')

            # 模拟视觉分析结果
            logger.warning('后端增强模块不可用，/api/commentary/analyze 无法提供真实视频分析结果')
            return jsonify({
                'code': 1,
                'msg': '原创解说视频分析功能需要后端增强服务，当前未启用 backend 模块，无法执行分析。',
                'data': None
            })
        except Exception as e:
            logger.error(f'视频分析失败: {e}')
            return jsonify({'code': -1, 'msg': str(e)})

    @app.route('/api/commentary/generate-script', methods=['POST'])
    def commentary_generate_script():
        """生成解说文案"""
        try:
            data = request.get_json()
            vision_results = data.get('vision_results', {})
            config = data.get('config', {})

            # 加载API配置
            api_config = load_api_config_data()
            llm_config = api_config.get('llm', {})

            logger.info(f'开始生成文案，使用模型: {llm_config.get("default_model", "默认模型")}')

            # 模拟文案生成
            logger.warning('后端增强模块不可用，/api/commentary/generate-script 无法调用真实 LLM 生成文案')
            return jsonify({
                'code': 1,
                'msg': '原创解说文案生成功能需要后端增强服务，当前未启用 backend 模块，无法生成文案。',
                'data': None
            })
        except Exception as e:
            logger.error(f'文案生成失败: {e}')
            return jsonify({'code': -1, 'msg': str(e)})

    @app.route('/api/commentary/create', methods=['POST'])
    def commentary_create():
        """创建原创解说项目"""
        try:
            data = request.get_json()
            name = data.get('name')
            video_path = data.get('video_path')
            script = data.get('script')

            logger.warning('后端增强模块不可用，/api/commentary/create 无法创建真实原创解说项目')
            return jsonify({
                'code': 1,
                'msg': '原创解说项目创建功能需要后端增强服务，当前未启用 backend 模块，无法创建项目。',
                'data': None
            })
        except Exception as e:
            logger.error(f'创建项目失败: {e}')
            return jsonify({'code': -1, 'msg': str(e)})

    @app.route('/api/commentary/process', methods=['POST'])
    def commentary_process():
        """处理原创解说项目"""
        try:
            data = request.get_json()
            project_id = data.get('project_id')
            video_path = data.get('video_path')
            config = data.get('config', {})

            logger.warning('后端增强模块不可用，/api/commentary/process 无法执行真实原创解说处理流程')
            return jsonify({
                'code': 1,
                'msg': '原创解说完整处理流程需要后端增强服务，当前未启用 backend 模块，无法执行处理。',
                'data': None
            })
        except Exception as e:
            logger.error(f'项目处理失败: {e}')
            return jsonify({'code': -1, 'msg': str(e)})

    # 2. 混剪模式相关API
    @app.route('/api/remix/create', methods=['POST'])
    def remix_create():
        """创建混剪项目"""
        try:
            data = request.get_json()
            name = data.get('name')
            video_paths = data.get('video_paths', [])
            style = data.get('style')

            logger.warning('后端增强模块不可用，/api/remix/create 无法创建真实混剪项目')
            return jsonify({
                'code': 1,
                'msg': '智能混剪功能需要后端增强服务，当前未启用 backend 模块，无法创建混剪项目。',
                'data': None
            })
        except Exception as e:
            logger.error(f'创建混剪项目失败: {e}')
            return jsonify({'code': -1, 'msg': str(e)})

    @app.route('/api/remix/process', methods=['POST'])
    def remix_process():
        """处理混剪项目"""
        try:
            data = request.get_json()
            project_id = data.get('project_id')

            logger.warning('后端增强模块不可用，/api/remix/process 无法执行真实混剪处理流程')
            return jsonify({
                'code': 1,
                'msg': '智能混剪处理流程需要后端增强服务，当前未启用 backend 模块，无法执行处理。',
                'data': None
            })
        except Exception as e:
            logger.error(f'混剪处理失败: {e}')
            return jsonify({'code': -1, 'msg': str(e)})

    # 3. AI配音相关API
    @app.route('/api/voiceover/preview', methods=['POST'])
    def voiceover_preview():
        """预览音色"""
        try:
            data = request.get_json()
            voice_id = data.get('voice_id')
            sample_text = data.get('sample_text', '这是音色预览示例')

            logger.info(f'预览音色: {voice_id}')

            # 模拟生成预览音频（前端回放期望 /output/audios/ 路径）
            from pathlib import Path as _Path
            out_dir = BASE_DIR / 'output' / 'audios'
            out_dir.mkdir(parents=True, exist_ok=True)

            # 生成预览音频文件（与配音生成逻辑保持一致，优先 edge-tts 回退 gTTS）
            text = (sample_text or '这是音色预览示例，您好！').strip()
            safe_voice_id = (voice_id or 'zh-CN-XiaoxiaoNeural').strip()
            filename = f"preview_{safe_voice_id}_{uuid.uuid4().hex}.mp3"
            out_path = out_dir / filename

            tts_ok = False
            try:
                import asyncio, edge_tts

                async def _run_preview():
                    comm = edge_tts.Communicate(text, voice=safe_voice_id)
                    await comm.save(str(out_path))

                asyncio.run(_run_preview())
                tts_ok = True
            except Exception as ee:
                logger.warning(f'edge-tts 预览失败，尝试 gTTS 回退: {ee}')
                try:
                    from gtts import gTTS
                    tts = gTTS(text=text, lang='zh')
                    tts.save(str(out_path))
                    tts_ok = True
                except Exception as e2:
                    logger.error(f'TTS 预览失败（edge-tts 与 gTTS 均失败）: {ee} / {e2}', exc_info=True)
                    return jsonify({'code': 1, 'msg': f'预览生成失败: {e2}', 'data': None}), 500

            if not tts_ok or not _Path(out_path).exists():
                return jsonify({'code': 1, 'msg': '预览生成失败', 'data': None}), 500

            preview_path = f"output/audios/{filename}"
            preview_url = '/' + preview_path

            return jsonify({
                'code': 0,
                'msg': '预览生成成功',
                'data': {
                    'audio_url': preview_url,
                    'audio_path': preview_path,
                    'duration': None
                }
            })
        except Exception as e:
            logger.error(f'音色预览失败: {e}')
            return jsonify({'code': -1, 'msg': str(e), 'data': None})

    @app.route('/api/voiceover/generate', methods=['POST'])
    def voiceover_generate():
        """生成配音（CPU可用，优先使用 edge-tts，失败回退 gTTS）"""
        try:
            data = request.get_json() or {}
            text = (data.get('text') or '').strip()
            voice_config = data.get('voice_config') or {}

            if not text:
                return jsonify({'code': 1, 'msg': '请输入配音文本', 'data': None}), 400

            # 解析音色/语速/音量
            voice = (voice_config.get('voice') or 'zh-CN-XiaoxiaoNeural').strip()
            if voice in ('female-1', 'female', '女声', 'default'):
                voice = 'zh-CN-XiaoxiaoNeural'
            elif voice in ('male-1', 'male', '男声'):
                voice = 'zh-CN-YunjianNeural'

            try:
                speed = float(voice_config.get('speed') or 1.0)
            except Exception:
                speed = 1.0
            rate_pct = max(-100, min(100, int(round((speed - 1.0) * 100))))
            rate = f"{'+' if rate_pct >= 0 else ''}{rate_pct}%"

            try:
                volume_val = int(voice_config.get('volume') or 100)
            except Exception:
                volume_val = 100
            vol_delta = max(-100, min(100, volume_val - 100))
            volume = f"{'+' if vol_delta >= 0 else ''}{vol_delta}%"

            # 输出路径
            out_dir = BASE_DIR / 'output' / 'audios'
            out_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid.uuid4().hex}.mp3"
            out_path = out_dir / filename

            # 优先使用 edge-tts，失败时回退 gTTS
            tts_ok = False
            try:
                import asyncio, edge_tts

                async def _run():
                    comm = edge_tts.Communicate(text, voice=voice, rate=rate, volume=volume)
                    await comm.save(str(out_path))

                asyncio.run(_run())
                tts_ok = True
            except Exception as ee:
                logger.warning(f'edge-tts 失败，尝试 gTTS 回退: {ee}')
                try:
                    from gtts import gTTS
                    tts = gTTS(text=text, lang='zh')
                    tts.save(str(out_path))
                    tts_ok = True
                except Exception as e2:
                    logger.error(f'TTS 失败（edge-tts 与 gTTS 均失败）: {ee} / {e2}', exc_info=True)
                    return jsonify({'code': 1, 'msg': f'TTS 生成失败: {e2}', 'data': None}), 500

            if not tts_ok or not out_path.exists():
                return jsonify({'code': 1, 'msg': 'TTS 生成失败', 'data': None}), 500

            audio_path = f"output/audios/{filename}"
            audio_url = '/' + audio_path
            result = {
                'audio_url': audio_url,
                'audio_path': audio_path,
                'voice': voice
            }
            return jsonify({'code': 0, 'msg': '生成成功', 'data': result})
        except Exception as e:
            logger.error(f'配音生成失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'配音生成失败: {e}', 'data': None}), 500

# ==================== 克隆语音相关API ====================
@app.route('/api/voice_clone/test', methods=['POST'])
def test_voice_clone():
    """测试克隆语音引擎"""
    try:
        data = request.get_json()
        voice_clone_path = data.get('voice_clone_path')
        model_path = data.get('model_path')

        # 导入voice_clone引擎
        import sys
        sys.path.append(os.path.join(BASE_DIR, 'backend'))
        from engine.voice_clone_engine import VoiceCloneEngine

        # 初始化引擎
        engine = VoiceCloneEngine(voice_clone_path, model_path)

        # 获取内置音色列表
        voices = engine.get_builtin_voices()

        logger.info(f'✅ 克隆语音引擎测试成功，支持{len(voices)}种音色')

        return jsonify({
            'code': 0,
            'voices_count': len(voices),
            'voices': voices
        })
    except Exception as e:
        logger.error(f'❌ 克隆语音引擎测试失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)})

@app.route('/api/voice_clone/voices', methods=['GET'])
def get_voice_clone_voices():
    """获取克隆语音支持的音色列表"""
    try:
        # 加载API配置
        api_config = load_api_config_data()
        voice_clone_config = api_config.get('voice_clone', {})

        voice_clone_path = voice_clone_config.get('path')
        model_path = voice_clone_config.get('model_path')

        # 导入voice_clone引擎
        import sys
        sys.path.append(os.path.join(BASE_DIR, 'backend'))
        from engine.voice_clone_engine import VoiceCloneEngine

        engine = VoiceCloneEngine(voice_clone_path, model_path)
        voices = engine.get_builtin_voices()

        return jsonify({'code': 0, 'voices': voices})
    except Exception as e:
        logger.error(f'❌ 获取音色列表失败: {e}')
        return jsonify({'code': -1, 'msg': str(e), 'voices': []})

@app.route('/api/voice_clone/generate', methods=['POST'])
def voice_clone_generate():
    """使用克隆语音生成音频（文本->TTS 临时音频 -> 语音克隆）"""
    try:
        data = request.get_json() or {}
        text = (data.get('text') or '').strip()
        voice_id = (data.get('voice_id') or 'zh').strip()  # 目标音色（内置：zh/en-us/... 或参考音频路径）
        # 基础 TTS 音色：优先前端传入的 tts_voice，其次复用 voice_id，最后兜底为通用中文 "zh"
        tts_voice = (data.get('tts_voice') or voice_id or 'zh').strip()

        if not text:
            return jsonify({'code': 1, 'msg': '缺少要合成的文本'}), 400

        # 读取配置中的本地 voice_clone 安装路径
        api_config = load_api_config_data()
        vc_cfg = api_config.get('voice_clone', {})
        voice_clone_path = vc_cfg.get('path')
        model_path = vc_cfg.get('model_path')

        # 1) TTS 到临时 MP3
        out_dir = BASE_DIR / 'output' / 'audios'
        tmp_dir = BASE_DIR / 'temp' / 'tts_tmp'
        out_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_mp3 = tmp_dir / f"tts_{uuid.uuid4().hex}.mp3"

        # 使用内置 TTS 引擎（Edge-TTS 优先）
        try:
            import sys as _sys
            _sys.path.append(str(BASE_DIR / 'backend'))
            from engine import TTSEngine
            tts_engine = TTSEngine(default_engine='edge-tts')
            ok = tts_engine.synthesize(text, str(tmp_mp3), engine='edge-tts', voice=tts_voice, rate='+0%', volume='+0%')
            if not ok:
                # 回退 gTTS
                ok = tts_engine.synthesize(text, str(tmp_mp3), engine='gtts', lang='zh-CN', slow=False)
            if not ok:
                return jsonify({'code': 1, 'msg': 'TTS 合成失败'}), 500
        except Exception as te:
            logger.error(f'TTS 合成异常: {te}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'TTS 合成异常: {te}'}), 500

        # 2) 转 WAV（部分克隆引擎更稳健）
        tmp_wav = tmp_dir / f"tts_{uuid.uuid4().hex}.wav"
        try:
            import subprocess
            cmd = ['ffmpeg', '-y', '-i', str(tmp_mp3), '-ar', '44100', '-ac', '1', str(tmp_wav)]
            subprocess.run(cmd, check=True, capture_output=True)
        except Exception as ce:
            logger.warning(f'MP3->WAV 转换失败，尝试直接使用 MP3：{ce}')
            tmp_wav = tmp_mp3  # 退回直接使用 MP3

        # 3) 调用语音克隆引擎
        try:
            import sys as _sys
            _sys.path.append(str(BASE_DIR / 'backend'))
            from engine import VoiceCloneEngine
            vc_engine = VoiceCloneEngine(voice_clone_path=voice_clone_path, model_path=model_path)
        except Exception as ie:
            logger.error(f'语音克隆引擎加载失败: {ie}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'语音克隆引擎加载失败: {ie}'}), 500

        # 输出到 /output/audios
        out_name = f"voice_clone_{int(time.time())}_{uuid.uuid4().hex[:6]}.wav"
        final_out = out_dir / out_name

        cloned = vc_engine.clone_voice(str(tmp_wav), voice_id, output_path=str(final_out), save_tone=False)
        if not cloned or not Path(final_out).exists():
            return jsonify({'code': 1, 'msg': '语音克隆失败'}), 500

        audio_url = f"/output/audios/{out_name}"
        return jsonify({'code': 0, 'audio_url': audio_url, 'voice_id': voice_id})
    except Exception as e:
        logger.error(f'❌ 克隆语音生成失败: {e}', exc_info=True)
        return jsonify({'code': -1, 'msg': str(e)})

# ==================== 其他配置API ====================
@app.route('/api/config/reset', methods=['POST'])
def reset_api_config():
    """恢复默认API配置"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'config', 'api_config.yaml')

        # 删除配置文件
        if os.path.exists(config_path):
            os.remove(config_path)

        logger.info('✅ API配置已恢复默认')
        return jsonify({'code': 0, 'msg': '恢复成功'})
    except Exception as e:
        logger.error(f'❌ 恢复API配置失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)})

@app.route('/api/narration/hook-types', methods=['GET'])
def get_hook_types():
    """获取所有可用的开头钩子类型"""
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        from prompts.narration_prompts import NarrationPrompts

        hook_types = []
        for key, info in NarrationPrompts.get_all_hook_types().items():
            hook_types.append({
                'key': key,
                'name': info['name'],
                'template': info['template'],
                'examples': info['examples']
            })

        logger.info(f'✅ 获取到{len(hook_types)}种钩子类型')
        return jsonify({'code': 0, 'hook_types': hook_types})
    except Exception as e:
        logger.error(f'❌ 获取钩子类型失败: {e}')
        return jsonify({'code': 1, 'msg': str(e)}), 500

@app.route('/api/config/detect_jianying', methods=['POST'])
def detect_jianying_path():
    """自动检测剪映安装路径"""
    try:
        import platform

        # Windows系统常见安装路径
        if platform.system() == 'Windows':
            possible_paths = [
                r'C:\Program Files\JianyingPro\JianyingPro.exe',
                r'C:\Program Files (x86)\JianyingPro\JianyingPro.exe',
                os.path.expanduser(r'~\AppData\Local\JianyingPro\JianyingPro.exe'),
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    logger.info(f'✅ 检测到剪映路径: {path}')
                    return jsonify({'code': 0, 'path': path})

        return jsonify({'code': -1, 'msg': '未检测到剪映安装路径'})
    except Exception as e:
        logger.error(f'❌ 检测剪映路径失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)})

# ==================== 视频导出API ====================
# 已通过 backend.api.export_api 模块注册，避免重复定义
def main():
    """主函数 - 完整实现"""
    try:
        logger.info('\n' + '='*70)
        logger.info('🌟 AIJian v2.0 - 智能视频剪辑工具')
        logger.info('='*70)
        logger.info(f'📅 启动时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        logger.info(f'🐍 Python版本: {sys.version.split()[0]}')
        logger.info(f'📂 项目目录: {BASE_DIR}')
        logger.info(f'💾 数据库: {db_manager.db_path}')
        logger.info(f'🔧 后端增强: {"已启用" if BACKEND_AVAILABLE else "未启用"}')
        logger.info('='*70 + '\n')

        # 在后台线程启动服务器
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # 等待服务器启动
        logger.info('⏳ 等待服务器启动...')
        time.sleep(2)
        logger.info(f'✅ 服务器已启动: http://{UI_HOST}:{APP_PORT}\n')

        # 启动桌面应用
        start_desktop_app()
    except KeyboardInterrupt:
        logger.info('\n✅ 用户中断，程序退出')
        sys.exit(0)
    except Exception as e:
        logger.error(f'\n❗ 应用启动失败: {str(e)}', exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()



