# AIJian - 完整开发文档 Part 3

**业务服务层、任务队列、部署打包与开发路线图**

---

## 9. 业务服务层

### 9.1 项目管理服务 (services/project_service.py)
```python
import logging
import uuid
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from config.database import get_db_session
from models.project import Project
from models.material import Material

logger = logging.getLogger(__name__)

class ProjectService:
    """项目管理服务"""
    
    def __init__(self):
        self.project_base_dir = Path('static/draft')
        self.project_base_dir.mkdir(parents=True, exist_ok=True)
    
    def get_all_projects(self, project_type: Optional[str] = None) -> List[Dict]:
        """获取所有项目列表"""
        with get_db_session() as session:
            query = session.query(Project).filter(Project.deleted_at.is_(None))
            
            if project_type:
                query = query.filter(Project.type == project_type)
            
            projects = query.order_by(Project.created_at.desc()).all()
            
            return [project.to_dict() for project in projects]
    
    def get_project(self, project_id: str) -> Optional[Dict]:
        """获取项目详情"""
        with get_db_session() as session:
            project = session.query(Project).filter(
                Project.id == project_id,
                Project.deleted_at.is_(None)
            ).first()
            
            if not project:
                return None
            
            # 包含素材列表
            result = project.to_dict()
            result['materials'] = [m.to_dict() for m in project.materials]
            
            return result
    
    def create_project(
        self,
        name: str,
        project_type: str,
        description: str = '',
        template: Optional[str] = None
    ) -> Dict:
        """创建项目"""
        logger.info(f'创建项目: name={name}, type={project_type}')
        
        project_id = str(uuid.uuid4())
        
        # 创建项目目录
        project_dir = self.project_base_dir / project_type / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # 如果使用模板，则复制模板文件
        if template:
            self._apply_template(project_dir, template)
        
        # 创建数据库记录
        with get_db_session() as session:
            project = Project(
                id=project_id,
                name=name,
                type=project_type,
                description=description,
                config=json.dumps({
                    'template': template,
                    'output_format': 'mp4',
                    'quality': 'high'
                }, ensure_ascii=False)
            )
            
            session.add(project)
            session.commit()
            
            logger.info(f'✅ 项目创建成功: {project_id}')
            
            return project.to_dict()
    
    def update_project(self, project_id: str, data: Dict) -> Dict:
        """更新项目"""
        logger.info(f'更新项目: {project_id}')
        
        with get_db_session() as session:
            project = session.query(Project).filter(
                Project.id == project_id
            ).first()
            
            if not project:
                raise ValueError(f'项目不存在: {project_id}')
            
            # 更新字段
            if 'name' in data:
                project.name = data['name']
            if 'description' in data:
                project.description = data['description']
            if 'status' in data:
                project.status = data['status']
            if 'config' in data:
                project.config_dict = data['config']
            if 'thumbnail' in data:
                project.thumbnail = data['thumbnail']
            
            project.updated_at = datetime.utcnow()
            
            session.commit()
            
            logger.info(f'✅ 项目更新成功: {project_id}')
            
            return project.to_dict()
    
    def delete_project(self, project_id: str):
        """删除项目（软删除）"""
        logger.info(f'删除项目: {project_id}')
        
        with get_db_session() as session:
            project = session.query(Project).filter(
                Project.id == project_id
            ).first()
            
            if not project:
                raise ValueError(f'项目不存在: {project_id}')
            
            # 软删除
            project.deleted_at = datetime.utcnow()
            session.commit()
            
            logger.info(f'✅ 项目删除成功: {project_id}')
    
    def hard_delete_project(self, project_id: str):
        """彻底删除项目（包含文件）"""
        logger.info(f'彻底删除项目: {project_id}')
        
        with get_db_session() as session:
            project = session.query(Project).filter(
                Project.id == project_id
            ).first()
            
            if not project:
                raise ValueError(f'项目不存在: {project_id}')
            
            # 删除项目目录
            project_dir = self.project_base_dir / project.type / project_id
            if project_dir.exists():
                shutil.rmtree(project_dir)
            
            # 删除数据库记录
            session.delete(project)
            session.commit()
            
            logger.info(f'✅ 项目彻底删除成功: {project_id}')
    
    def save_video(self, project_id: str, file) -> Dict:
        """保存上传的视频文件"""
        logger.info(f'保存视频: project_id={project_id}, filename={file.filename}')
        
        # 获取项目信息
        with get_db_session() as session:
            project = session.query(Project).filter(
                Project.id == project_id
            ).first()
            
            if not project:
                raise ValueError(f'项目不存在: {project_id}')
            
            # 保存文件
            project_dir = self.project_base_dir / project.type / project_id
            video_dir = project_dir / 'videos'
            video_dir.mkdir(exist_ok=True)
            
            file_path = video_dir / file.filename
            file.save(str(file_path))
            
            # 获取视频信息
            from engine.ffmpeg_engine import FFmpegEngine
            ffmpeg = FFmpegEngine()
            video_info = ffmpeg.get_video_info(str(file_path))
            
            # 创建素材记录
            material = Material(
                id=str(uuid.uuid4()),
                project_id=project_id,
                type='video',
                name=file.filename,
                path=str(file_path),
                size=file_path.stat().st_size,
                duration=video_info['duration'],
                width=video_info['video']['width'],
                height=video_info['video']['height'],
                fps=video_info['video']['fps'],
                codec=video_info['video']['codec'],
                metadata=json.dumps(video_info, ensure_ascii=False)
            )
            
            session.add(material)
            session.commit()
            
            logger.info(f'视频保存成功: {file_path}')
            
            return material.to_dict()
    
    def export_project(
        self,
        project_id: str,
        format: str = 'mp4',
        quality: str = 'high',
        output_path: Optional[str] = None
    ) -> str:
        """导出项目（创建导出任务）"""
        logger.info(f'导出项目: project_id={project_id}, format={format}, quality={quality}')
        from services.task_service import TaskService
        
        task_service = TaskService()
        task_id = task_service.create_task(
            task_type='project_export',
            project_id=project_id,
            input_data={
                'format': format,
                'quality': quality,
                'output_path': output_path
            }
        )
        
        # 启动导出任务
        task_service.start_export_task(task_id)
        
        return task_id
    
    def _apply_template(self, project_dir: Path, template_name: str):
        """应用项目模板（扩展示例）
        注意：当前实际代码中未实现基于 resource/template json 目录的文件级模板复制逻辑，
        仅在 projects.config 中保存 template 字段用于标记项目模板类型。
        本示例用于说明一种可扩展实现方式。"""
        template_dir = Path('resource/template json') / template_name
        
        if template_dir.exists():
            # 复制模板文件
            for file in template_dir.iterdir():
                if file.is_file():
                    shutil.copy(file, project_dir / file.name)
import uuid
import json
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Callable
from datetime import datetime
from queue import Queue

from config.database import get_db_session
from models.task import Task

logger = logging.getLogger(__name__)

class TaskService:
    """任务管理服务（扩展示例）
    说明：本示例展示了一种基于数据库 + 内部队列 + 工作线程的任务管理设计，当前实际实现位于 backend/services/task_service.py，采用 DatabaseManager + Socket.IO + 各处理引擎的组合方式。本段代码可作为后续扩展架构的参考。"""
    
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.task_queue = Queue()
        self.running_tasks = {}  # task_id -> thread
        self.task_callbacks = {}  # task_id -> callback
        
        # 启动任务处理工作线程
        self.worker_thread = threading.Thread(
            target=self._task_worker,
            daemon=True
        )
        self.worker_thread.start()
    
    def create_task(
        self,
        task_type: str,
        project_id: Optional[str] = None,
        input_data: Optional[Dict] = None
    ) -> str:
        """创建任务"""
        task_id = str(uuid.uuid4())
        
        with get_db_session() as session:
            task = Task(
                id=task_id,
                project_id=project_id,
                type=task_type,
                status='pending',
                input_data=json.dumps(input_data or {}, ensure_ascii=False)
            )
            
            session.add(task)
            session.commit()
        
        logger.info(f'✅ 任务创建成功: {task_id} ({task_type})')
        
        return task_id
    
    def start_task(self, data: Dict):
        """启动任务（加入内部队列）"""
        task_id = data.get('task_id')
        task_type = data.get('task_type')
        task_data = data.get('data', {})
        
        logger.info(f'启动任务: {task_id} ({task_type})')
        
        # 添加到任务队列
        self.task_queue.put({
            'task_id': task_id,
            'task_type': task_type,
            'data': task_data
        })
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        logger.info(f'取消任务: {task_id}')
        
        with get_db_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            
            if task:
                task.status = 'cancelled'
                task.completed_at = datetime.utcnow()
                session.commit()
        
        # 发送任务取消通知
        if self.socketio:
            self.socketio.emit('task_cancelled', {'task_id': task_id})
    
    def update_progress(self, task_id: str, progress: float, status: str = ''):
        """更新任务进度"""
        with get_db_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            
            if task:
                task.progress = progress
                session.commit()
        
        # 发送进度更新
        if self.socketio:
            self.socketio.emit('task_progress', {
                'task_id': task_id,
                'progress': progress,
                'status': status
            })
    
    def complete_task(self, task_id: str, output_data: Optional[Dict] = None):
        """任务完成"""
        logger.info(f'任务完成: {task_id}')
        
        with get_db_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            
            if task:
                task.status = 'completed'
                task.progress = 100.0
                task.completed_at = datetime.utcnow()
                if output_data:
                    task.output_data = json.dumps(output_data, ensure_ascii=False)
                session.commit()
        
        # 发送完成通知
        if self.socketio:
            self.socketio.emit('task_complete', {
                'task_id': task_id,
                'result': output_data
            })
    
    def fail_task(self, task_id: str, error: str):
        """任务失败"""
        logger.error(f'任务失败: {task_id} - {error}')
        
        with get_db_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            
            if task:
                task.status = 'failed'
                task.error_message = error
                task.completed_at = datetime.utcnow()
                session.commit()
        
        # 发送失败通知
        if self.socketio:
            self.socketio.emit('task_error', {
                'task_id': task_id,
                'error': error
            })
    
    def _task_worker(self):
        """任务处理工作线程"""
        logger.info('任务处理线程已启动')
        
        while True:
            try:
                # 从队列中获取任务
                task_info = self.task_queue.get(timeout=1)
                
                if task_info:
                    # 创建线程处理任务
                    thread = threading.Thread(
                        target=self._execute_task,
                        args=(task_info,)
                    )
                    thread.start()
                    
                    self.running_tasks[task_info['task_id']] = thread
            except Exception as e:
                # 队列为空或其他错误，稍后重试
                time.sleep(0.1)
    
    def _execute_task(self, task_info: Dict):
        """执行具体任务"""
        task_id = task_info['task_id']
        task_type = task_info['task_type']
        task_data = task_info['data']
        
        try:
            logger.info(f'开始执行任务: {task_id} ({task_type})')
            
            # 更新任务状态
            with get_db_session() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.status = 'running'
                    task.started_at = datetime.utcnow()
                    session.commit()
            
            # 根据任务类型调用对应的处理函数
            if task_type == 'video_cut':
                self._handle_video_cut(task_id, task_data)
            elif task_type == 'video_merge':
                self._handle_video_merge(task_id, task_data)
            elif task_type == 'tts':
                self._handle_tts(task_id, task_data)
            elif task_type == 'asr':
                self._handle_asr(task_id, task_data)
            elif task_type == 'project_export':
                self._handle_export(task_id, task_data)
            elif task_type == 'model_download':
                self._handle_model_download(task_id, task_data)
            else:
                raise ValueError(f'未知任务类型: {task_type}')
            
            logger.info(f'✅ 任务执行成功: {task_id}')
        
        except Exception as e:
            logger.error(f'❌ 任务执行失败: {task_id} - {e}', exc_info=True)
            self.fail_task(task_id, str(e))
        
        finally:
            # 清理运行中任务记录
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    def _handle_video_cut(self, task_id: str, data: Dict):
        """处理视频剪辑任务"""
        from engine.ffmpeg_engine import FFmpegEngine
        
        ffmpeg = FFmpegEngine()
        
        video_path = data['video_path']
        cuts = data['cuts']
        output_path = data.get('output_path')
        
        self.update_progress(task_id, 10, '准备剪辑')
        
        # 执行剪辑
        output_files = []
        for i, cut in enumerate(cuts):
            progress = 10 + (i / len(cuts)) * 80
            self.update_progress(task_id, progress, f'剪辑片段 {i+1}/{len(cuts)}')
            
            output_file = f'{output_path}_part_{i}.mp4' if output_path else None
            ffmpeg.cut_video(
                video_path,
                output_file,
                cut['start'],
                cut['end']
            )
            output_files.append(output_file)
        
        self.update_progress(task_id, 95, '合并片段')
        
        # 如果需要合并
        if len(output_files) > 1 and data.get('merge', True):
            final_output = output_path or 'output.mp4'
            ffmpeg.merge_videos(output_files, final_output)
            
            # 删除临时文件
            for f in output_files:
                if f and os.path.exists(f):
                    os.remove(f)
            output_files = [final_output]
        
        self.complete_task(task_id, {'output_files': output_files})
    
    def _handle_tts(self, task_id: str, data: Dict):
        """处理TTS任务"""
        from engine.tts_engine import TTSEngine
        
        tts = TTSEngine()
        
        text = data['text']
        voice = data.get('voice', 'zh-CN-XiaoxiaoNeural')
        output_path = data.get('output_path')
        
        self.update_progress(task_id, 20, '准备生成语音')
        
        # 生成语音
        output_file = tts.generate(
            text=text,
            voice=voice,
            output_path=output_path,
            speed=data.get('speed', 1.0),
            volume=data.get('volume', 1.0),
            pitch=data.get('pitch', 0)
        )
        
        self.update_progress(task_id, 90, '语音生成完成')
        
        self.complete_task(task_id, {'audio_file': output_file})
    
    def _handle_asr(self, task_id: str, data: Dict):
        """处理ASR任务"""
        from engine.asr_engine import ASREngine
        
        asr = ASREngine()
        
        audio_path = data['audio_path']
        language = data.get('language', 'zh')
        
        self.update_progress(task_id, 20, '准备识别语音')
        
        # 璇嗗埆璇煶
        segments, info = asr.transcribe(
            audio_path=audio_path,
            language=language
        )
        
        self.update_progress(task_id, 90, '识别完成')
        
        self.complete_task(task_id, {
            'segments': segments,
            'info': info
        })
```

---

## 10. API 接口完整说明

### 10.1 API 响应格式

#### 10.1.1 标准响应格式
```json
{
  "code": 0,
  "msg": "操作成功",
  "data": {
    // 实际数据
  }
}
```

#### 10.1.2 错误响应格式
```json
{
  "code": 500,
  "msg": "错误描述",
  "error": "详细错误信息"
}
```

### 10.2 API 端点一览

#### 10.2.1 项目管理 API

| 方法   | 端点                      | 说明           |
|--------|---------------------------|----------------|
| GET    | `/api/project/list`       | 获取项目列表   |
| GET    | `/api/project/detail/<id>` | 获取项目详情  |
| POST   | `/api/project/create`     | 创建项目       |
| PUT    | `/api/project/update/<id>` | 更新项目      |
| DELETE | `/api/project/delete/<id>` | 删除项目      |
| POST   | `/api/project/upload`     | 上传视频       |
| POST   | `/api/project/export/<id>` | 导出项目      |

#### 10.2.2 视频处理 API

| 方法   | 端点                      | 说明           |
|--------|---------------------------|----------------|
| POST   | `/api/video/analyze`      | 分析视频       |
| POST   | `/api/video/cut`          | 剪辑视频       |
| POST   | `/api/video/merge`        | 合并视频       |
| POST   | `/api/video/add-audio`    | 添加音频       |
| POST   | `/api/video/scene-detect` | 场景检测       |

#### 10.2.3 音频处理 API

| 方法   | 端点                      | 说明           |
|--------|---------------------------|----------------|
| POST   | `/api/audio/tts`          | 文本转语音     |
| POST   | `/api/audio/asr`          | 语音识别       |
| POST   | `/api/audio/mix`          | 混合音频       |
| POST   | `/api/audio/denoise`      | 音频降噪       |
| GET    | `/api/audio/voice-list`   | 获取音色列表   |

#### 10.2.4 AI 模型 API

| 方法   | 端点                      | 说明           |
|--------|---------------------------|----------------|
| GET    | `/api/model/list`         | 获取模型列表   |
| POST   | `/api/model/download`     | 下载模型       |
| DELETE | `/api/model/delete`       | 删除模型       |
| GET    | `/api/model/info/<id>`    | 获取模型信息   |

---

## 11. 部署与打包

### 11.1 Windows 打包方案

#### 11.1.1 使用 PyInstaller 打包

##### 创建打包配置文件 (build.spec)
```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[
        ('ffmpeg.exe', '.'),
        ('ffprobe.exe', '.'),
        ('ffplay.exe', '.'),
    ],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('config', 'config'),
        ('resource', 'resource'),
        ('favicon.ico', '.'),
    ],
    hiddenimports=[
        'flask',
        'flask_cors',
        'flask_socketio',
        'webview',
        'edge_tts',
        'faster_whisper',
        'torch',
        'transformers',
        'av',
        'librosa',
        'soundfile',
        'scipy',
        'numpy',
        'PIL',
        'cv2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AIJian',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='favicon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AIJian',
)
```

##### 打包脚本示例 (scripts/build.py)
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 打包脚本
"""

import subprocess
import shutil
from pathlib import Path
import sys

def build():
    """执行打包"""
    print('=' * 70)
    print('开始打包 AIJian')
    print('=' * 70)
    
    # 清理旧的打包文件
    print('\n[1/4] 清理旧文件...')
    dist_dir = Path('dist')
    build_dir = Path('build')
    
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    # 使用 PyInstaller 打包
    print('\n[2/4] 执行 PyInstaller 打包...')
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'build.spec'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print('打包失败：')
        print(result.stderr)
        sys.exit(1)
    
    print('PyInstaller 打包完成')
    
    # 复制额外文件
    print('\n[3/4] 复制额外文件...')
    output_dir = dist_dir / 'JJYB_AI'
    
    # 复制 VC 运行库
    vc_dir = Path('VCRedistributable')
    shutil.copytree(vc_dir, output_dir / 'VCRedistributable')
    
    # 复制 README
    shutil.copy('README.md', output_dir / 'README.md')
    
    # 创建启动批处理
    with open(output_dir / '启动.bat', 'w', encoding='utf-8') as f:
        f.write('@echo off\n')
        f.write('chcp 65001 >nul 2>&1\n')
        f.write('start JJYB_AI.exe\n')
    
    print('额外文件复制完成')
    
    # 创建安装包（可选）
    print('\n[4/4] 创建安装包...')
    # 可使用 Inno Setup 创建安装程序
    # 需要先安装 Inno Setup 并配置命令行工具
    
    print('\n' + '=' * 70)
    print('打包完成')
    print(f'输出目录: {output_dir}')
    print('=' * 70)

if __name__ == '__main__':
    build()
```

#### 11.1.2 使用 Nuitka 编译

```python
# scripts/build_nuitka.py
import subprocess
import sys

def build_with_nuitka():
    """使用 Nuitka 编译"""
    cmd = [
        'python', '-m', 'nuitka',
        '--standalone',
        '--windows-disable-console',
        '--windows-icon-from-ico=favicon.ico',
        '--include-data-dir=templates=templates',
        '--include-data-dir=static=static',
        '--include-data-dir=config=config',
        '--include-data-dir=resource=resource',
        '--include-data-file=ffmpeg.exe=ffmpeg.exe',
        '--include-data-file=ffprobe.exe=ffprobe.exe',
        '--enable-plugin=numpy',
        '--enable-plugin=torch',
        '--follow-imports',
        '--output-dir=build_nuitka',
        'frontend/app.py'
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print('Nuitka 编译成功')
    else:
        print('Nuitka 编译失败')
        sys.exit(1)

if __name__ == '__main__':
    build_with_nuitka()
```

### 11.2 Docker 部署

> 说明：本小节提供的是 *可选的* Docker 部署示例。当前项目默认作为 Windows 桌面应用
> 运行，使用本地 Flask 进程 + PyInstaller 打包；仓库中默认不包含实际的 Dockerfile /
> docker-compose.yml 文件。如需容器化部署，可参考下列示例自行创建配置文件。

#### 11.2.1 Dockerfile
```dockerfile
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 拷贝依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝应用文件
COPY . .

# 暴露端口
EXPOSE 5000

# 设置环境变量
ENV PYTHONIOENCODING=utf-8
ENV PYTHONLEGACYWINDOWSSTDIO=utf-8
ENV PYTHONUTF8=1

# 启动命令
CMD ["python", "app.py"]
```

#### 11.2.2 docker-compose.yml
```yaml
version: '3.8'

services:
  AIJian:
    build: .
    container_name: AIJian
    ports:
      - "5000:5000"
    volumes:
      - ./static:/app/static
      - ./resource:/app/resource
      - ./log:/app/log
      - ./data:/app/data
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/AIJian
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped
  
  db:
    image: postgres:15-alpine
    container_name: AIJian-db
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=AIJian
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
  
  redis:
    image: redis:7-alpine
    container_name: AIJian-redis
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 11.3 生产环境配置

> 说明：本小节为 *可选的* 生产环境部署参考示例。当前版本默认仍通过内置 Flask
> 开发服务器 + 桌面封装运行，并不依赖 Gunicorn / Nginx；只有在需要真正的 Web
> 服务器部署时，才建议基于这里的配置做进一步扩展。

#### 11.3.1 使用 Gunicorn + Nginx

##### Gunicorn 配置 (gunicorn_config.py)
```python
import multiprocessing

# 绑定地址
bind = "127.0.0.1:5000"

# Worker 进程数
workers = multiprocessing.cpu_count() * 2 + 1

# Worker 类型（支持 WebSocket）
worker_class = "gevent"

# 超时时间
timeout = 120

# 最大请求数
max_requests = 1000
max_requests_jitter = 50

# 日志设置
accesslog = "log/gunicorn_access.log"
errorlog = "log/gunicorn_error.log"
loglevel = "info"

# Preload
preload_app = True
```

##### Nginx 配置
```nginx
upstream AIJian {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name example.com;
    
    client_max_body_size 16G;
    
    location / {
        proxy_pass http://AIJian;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /static {
        alias /path/to/AIJian/static;
        expires 30d;
    }
}
```

##### 启动脚本示例 (scripts/start_prod.sh)
```bash
#!/bin/bash

# 激活虚拟环境
source venv/bin/activate

# 启动 Gunicorn
gunicorn -c gunicorn_config.py app:app
```

---

## 12. 开发路线图

### 12.1 MVP 版本 (v1.0) - 基础功能

**开发周期**：2-3 个月

#### 核心功能
- ✅ 项目创建与管理
- ✅ 视频上传与预览
- ✅ 基础视频剪辑（裁剪、合并）
- ✅ TTS 文本转语音
- ✅ ASR 语音识别
- ✅ 简单场景检测
- ✅ 视频导出

#### 技术实现
- Flask 后端
- PyWebView 桌面 GUI
- FFmpeg 视频处理
- Edge TTS 文本转语音
- Whisper ASR
- SQLite 数据库

### 12.2 增强版本 (v2.0) - AI 功能

**开发周期**：3-4 个月

> 说明：本节为 v2.0 的目标规划说明。当前开源 Windows 桌面版已经实现
> Edge/gTTS/Azure TTS、本地语音克隆（VoiceCloneEngine）、基于 faster-whisper
> 的自动字幕、PySceneDetect+OpenCV 场景检测、轻量级项目模板和批量配音等
> 核心功能；而 Coqui TTS、FunASR、TransNetV2，以及 PostgreSQL/Redis/Celery
> 等相关技术栈，均作为可选扩展示例或未来版本方向，默认不开启、仓库中
> 也不强制安装这些依赖。

#### 新增功能
- ✅ 智能剪辑模式
- ✅ 智能解说剪辑
- ✅ AI 文案生成
- ✅ 高质量 TTS（Coqui TTS，可选扩展）
- ✅ 语音克隆
- ✅ 批量处理
- ✅ 项目模板系统
- ✅ AI 违规检测

#### 技术升级
- PostgreSQL 数据库
- Redis 缓存
- Celery 任务队列
- TransNetV2 场景检测（可选扩展）
- GPT 文案生成与整合
- FunASR 中文 ASR 优化（可选扩展）

### 12.3 专业版本 (v3.0) - 高阶功能

**开发周期**：4-6 个月

#### 专业功能
- 🎬 多轨时间线剪辑器
- 👀 实时预览
- ✨ 高级特效系统
- 📝 AI 自动字幕
- 🎨 智能调色与滤镜
- 🌐 多语言翻译与配音
- 📺 支持 4K/高码率视频
- 🚀 GPU 加速
- 🤝 多端协同与协作
- 🔌 插件扩展系统

#### 技术架构
- 微服务架构
- Kubernetes 部署
- 分布式任务处理
- S3 对象存储或等价方案
- CDN 加速分发
- API 开放平台

### 12.4 企业版本 (v4.0) - 商业化

**开发周期**：6-8 个月

#### 企业功能
- 🧩 多租户系统
- 👥 团队协作与项目共享
- 🔐 细粒度权限管理
- 📜 审计日志与合规管理
- 🔗 完整 API 接口
- 🪝 Webhook 集成
- 🎨 品牌与界面自定义
- 🏢 私有化/本地化部署
- 📈 SLA 服务等级保障
- 📞 专业技术支持

#### 商业模式
- 免费版：基础功能
- 专业版：$29/月
- 团队版：$99/月
- 企业版：定制报价

---

## 13. 性能优化

### 13.1 前端优化

#### 13.1.1 资源压缩
```javascript
// 使用 Webpack 打包
// webpack.config.js
module.exports = {
    mode: 'production',
    optimization: {
        minimize: true,
        splitChunks: {
            chunks: 'all',
        },
    },
};
```

#### 13.1.2 路由懒加载
```javascript
// 路由懒加载
const routes = [
    {
        path: '/make-audio',
        component: () => import('./pages/MakeAudio.vue')
    }
];
```

#### 13.1.3 缓存策略
```javascript
// Service Worker 缓存
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open('AIJian-v1').then((cache) => {
            return cache.addAll([
                '/',
                '/static/js/common.js',
                '/static/js/editor-fixes.js',
                '/static/js/page-transition.js',
                '/favicon.svg',
                // ... 其他静态资源
            ]);
        })
    );
});
```

### 13.2 后端优化

> 说明：本节中的 Redis、Celery 等方案用于说明在「服务端/集群部署」场景下
> 的可选优化思路。当前开源 Windows 桌面版默认仅使用本地 SQLite 数据库
> + 内置任务线程处理，不依赖 Redis/Celery 等外部服务，读者可按需选用。

#### 13.2.1 数据库优化
```python
# 使用索引
class Project(Base):
    __table_args__ = (
        Index('idx_type_status', 'type', 'status'),
        Index('idx_created_deleted', 'created_at', 'deleted_at'),
    )

# 查询优化
def get_projects_optimized(session):
    return session.query(Project).options(
        joinedload(Project.materials),  # 预加载关联
        defer(Project.config)  # 延迟加载大字段
    ).filter(
        Project.deleted_at.is_(None)
    ).limit(50).all()
```

#### 13.2.2 缓存策略
```python
# Redis 缓存
from functools import lru_cache
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_project_cached(project_id):
    # 优先从缓存获取
    cached = redis_client.get(f'project:{project_id}')
    if cached:
        return json.loads(cached)
    
    # 从数据库查询
    project = get_project_from_db(project_id)
    
    # 写入缓存
    redis_client.setex(
        f'project:{project_id}',
        3600,  # 1 小时过期
        json.dumps(project)
    )
    
    return project
```

#### 13.2.3 异步处理
```python
# 使用 asyncio
import asyncio

async def process_videos(video_paths):
    tasks = [process_single_video(path) for path in video_paths]
    results = await asyncio.gather(*tasks)
    return results

# Celery 异步任务
from celery import Celery

celery_app = Celery('AIJian', broker='redis://localhost:6379/0')

@celery_app.task
def process_video_task(video_path):
    # 长时间运行的任务
    result = process_video(video_path)
    return result
```

### 13.3 AI 模型优化

> 说明：本节中的 ONNX 量化、多实例推理等内容属于 AI 模型层面的进阶优化
> 示例，主要面向服务器或云端部署场景。当前桌面版以本地模型推理为主，
> 并不强制要求进行 ONNX 量化或复杂的推理集群部署。

#### 13.3.1 模型量化
```python
# ONNX 量化
import onnxruntime as ort

# 使用量化模型
session = ort.InferenceSession(
    'model_quantized.onnx',
    providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
)
```

#### 13.3.2 批量处理
> 说明：下例为批量 TTS 的伪代码示例。当前项目中已通过
> `backend/services/voiceover_service.py` 的 `batch_generate_voiceovers`
> 方法和 `/api/voiceover/batch-generate` 接口实现批量配音能力。
```python
def batch_tts(texts, batch_size=8):
    """批量 TTS"""
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_results = tts_engine.generate_batch(batch)
        results.extend(batch_results)
    return results
```

---

## 14. 测试策略

### 14.1 单元测试

```python
# tests/test_video_service.py
import pytest
from services.video_service import VideoService

class TestVideoService:
    
    @pytest.fixture
    def video_service(self):
        return VideoService()
    
    def test_analyze_video(self, video_service):
        result = video_service.analyze_video('test.mp4')
        assert result['duration'] > 0
        assert result['width'] > 0
    
    def test_cut_video(self, video_service):
        output = video_service.cut_video(
            'test.mp4',
            start=10,
            end=20
        )
        assert Path(output).exists()
```

### 14.2 集成测试

```python
# tests/test_api.py
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_create_project(client):
    response = client.post('/api/project/create', json={
        'name': 'Test Project',
        'type': 'video'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['code'] == 0
```

### 14.3 性能测试

```python
# tests/test_performance.py
import time
import pytest

def test_video_processing_performance():
    start_time = time.time()
    
    result = process_video('test.mp4')
    
    end_time = time.time()
    duration = end_time - start_time
    
    # 确保处理时间在可接受范围内
    assert duration < 60  # 60 秒内完成
```

---

## 15. 总结

### 15.1 技术选型总结

| 技术层面   | 选择                 | 原因                                   |
|------------|----------------------|----------------------------------------|
| 前端框架   | Layui + jQuery       | 成熟稳定，适合桌面风格界面           |
| 后端框架   | Flask                | 简单轻量，便于快速开发与扩展         |
| 界面 GUI   | PyWebView           | 基于 Web 技术，跨平台                 |
| 数据库     | SQLite/PostgreSQL    | 从轻量到生产可平滑切换，适配不同规模 |
| 视频处理   | FFmpeg               | 行业标准，功能强大                   |
| AI 框架    | PyTorch/ONNX         | 生态完善，性能优良                   |

### 15.2 开发建议

1. **MVP 优先**：先实现核心功能，再逐步优化
2. **模块化设计**：保持代码解耦，有利于维护和扩展
3. **测试驱动**：编写单元测试，保障功能质量
4. **文档完善**：及时更新开发文档，方便团队协作
5. **性能监控**：持续关注性能指标，按需进行优化
6. **用户反馈**：收集真实用户反馈，持续迭代产品

### 15.3 最终目标

打造一款 *功能完善、性能优秀、体验友好* 的 AI 视频剪辑工具，让视频创作更加简单高效。

---

**文档到此结束！** 🎉

*如有任何问题或需要更详细的说明，请参考源代码仓库或联系开发团队。*

---

**版本历史：**
- v1.0.0 (2025-11-08): 初始版本
- v2.0.0（计划发布）: 增强 AI 功能
- v3.0.0（规划中）: 面向专业创作者的高级版本

**维护者** AIJian 开发团队  
**许可证** Proprietary  
**联系方式** [GitHub Issues](https://github.com/yourusername/AIJian/issues)


