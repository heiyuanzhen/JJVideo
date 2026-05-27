# AIJian - 完整开发文档 Part 2

**业务逻辑层、数据库设计与 AI 模型汇总**

---

## 6. 数据库设计

### 6.1 数据库选型方案

#### 6.1.1 SQLite 方案（推荐：单机版本）
```python
# config/database.py
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DATABASE_PATH = Path(__file__).parent.parent / 'data' / 'AIJian.db'

@contextmanager
def get_db_connection():
    """获取数据库连接（上下文管理器）"""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row  # 返回字典风格行
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
```

#### 6.1.2 PostgreSQL 方案（推荐：生产环境）
```python
# config/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import os

# 数据库 URL
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://user:password@localhost:5432/AIJian'
)

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

# Session 工厂
SessionLocal = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
)

# Base 基类
Base = declarative_base()

@contextmanager
def get_db_session():
    """获取数据库会话对象"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
```

### 6.2 数据表设计

#### 6.2.1 项目表 (projects)
```sql
CREATE TABLE projects (
    id VARCHAR(36) PRIMARY KEY,              -- UUID
    name VARCHAR(255) NOT NULL,              -- 项目名称
    type VARCHAR(50) NOT NULL,               -- 项目类型（audio/commentary/mixed）
    description TEXT,                        -- 项目描述
    status VARCHAR(20) DEFAULT 'draft',      -- 状态（draft/processing/completed/failed）
    config TEXT,                             -- 项目配置（JSON）
    thumbnail VARCHAR(500),                  -- 缩略图路径
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,               -- 逻辑删除时间戳
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
);
```

#### 6.2.2 素材表 (materials)
```sql
CREATE TABLE materials (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,         -- 所属项目 ID
    type VARCHAR(20) NOT NULL,               -- 类型（video/audio/image）
    name VARCHAR(255) NOT NULL,              -- 文件名
    path VARCHAR(500) NOT NULL,              -- 文件路径
    size BIGINT,                             -- 文件大小（字节）
    duration FLOAT,                          -- 时长（秒）
    width INTEGER,                           -- 宽度（视频/图片）
    height INTEGER,                          -- 高度（视频/图片）
    fps FLOAT,                               -- 帧率（视频）
    bitrate INTEGER,                         -- 码率
    codec VARCHAR(50),                       -- 编码格式
    metadata TEXT,                           -- 元数据（JSON）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    INDEX idx_project (project_id),
    INDEX idx_type (type)
);
```

#### 6.2.3 任务表 (tasks)
```sql
CREATE TABLE tasks (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36),                  -- 所属项目 ID（可选）
    type VARCHAR(50) NOT NULL,               -- 任务类型
    status VARCHAR(20) DEFAULT 'pending',    -- 状态（pending/running/completed/failed/cancelled）
    progress FLOAT DEFAULT 0,                -- 进度（0-100）
    input_data TEXT,                         -- 输入数据（JSON）
    output_data TEXT,                        -- 输出数据（JSON）
    error_message TEXT,                      -- 错误信息
    started_at TIMESTAMP,                    -- 开始时间
    completed_at TIMESTAMP,                  -- 完成时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
    INDEX idx_project (project_id),
    INDEX idx_status (status),
    INDEX idx_type (type)
);
```

#### 6.2.4 模型表 (ai_models)
```sql
CREATE TABLE ai_models (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,              -- 模型名称
    type VARCHAR(50) NOT NULL,               -- 模型类型（tts/asr/scene/etc）
    version VARCHAR(50),                     -- 版本
    path VARCHAR(500) NOT NULL,              -- 模型路径
    size BIGINT,                             -- 模型大小
    source VARCHAR(100),                     -- 来源（huggingface/modelscope/local）
    status VARCHAR(20) DEFAULT 'available',  -- 状态（available/downloading/error）
    config TEXT,                             -- 模型配置（JSON）
    description TEXT,                        -- 描述
    downloaded_at TIMESTAMP,                 -- 下载时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (type),
    INDEX idx_status (status)
);
```

#### 6.2.5 用户设置表 (user_settings)
```sql
CREATE TABLE user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(100) UNIQUE NOT NULL,        -- 配置键
    value TEXT,                              -- 配置值（JSON）
    category VARCHAR(50),                    -- 分类
    description TEXT,                        -- 描述
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category)
);
```

#### 6.2.6 操作日志表 (operation_logs)
```sql
CREATE TABLE operation_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(36),                     -- 用户 ID（预留）
    action VARCHAR(100) NOT NULL,            -- 操作类型
    resource_type VARCHAR(50),               -- 资源类型
    resource_id VARCHAR(36),                 -- 资源 ID
    details TEXT,                            -- 详细信息（JSON）
    ip_address VARCHAR(45),                  -- IP 地址
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_action (action),
    INDEX idx_resource (resource_type, resource_id),
    INDEX idx_created (created_at)
);
```

### 6.3 数据模型（SQLAlchemy ORM）

#### 6.3.1 项目模型 (models/project.py)
```python
from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import json

from config.database import Base

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    description = Column(Text)
    status = Column(String(20), default='draft')
    config = Column(Text)  # JSON 字符串
    thumbnail = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # 关联关系
    materials = relationship('Material', back_populates='project', cascade='all, delete-orphan')
    tasks = relationship('Task', back_populates='project')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'status': self.status,
            'config': json.loads(self.config) if self.config else {},
            'thumbnail': self.thumbnail,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def config_dict(self):
        """获取配置字典"""
        return json.loads(self.config) if self.config else {}
    
    @config_dict.setter
    def config_dict(self, value):
        """设置配置字典"""
        self.config = json.dumps(value, ensure_ascii=False)
```

#### 6.3.2 素材模型 (models/material.py)
```python
from sqlalchemy import Column, String, Integer, BigInteger, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import json

from config.database import Base

class Material(Base):
    __tablename__ = 'materials'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    type = Column(String(20), nullable=False)
    name = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)
    size = Column(BigInteger)
    duration = Column(Float)
    width = Column(Integer)
    height = Column(Integer)
    fps = Column(Float)
    bitrate = Column(Integer)
    codec = Column(String(50))
    metadata = Column(Text)  # JSON 字符串
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    project = relationship('Project', back_populates='materials')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'type': self.type,
            'name': self.name,
            'path': self.path,
            'size': self.size,
            'duration': self.duration,
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'bitrate': self.bitrate,
            'codec': self.codec,
            'metadata': json.loads(self.metadata) if self.metadata else {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
```

#### 6.3.3 任务模型 (models/task.py)
```python
from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import json

from config.database import Base

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    type = Column(String(50), nullable=False)
    status = Column(String(20), default='pending')
    progress = Column(Float, default=0.0)
    input_data = Column(Text)  # JSON 字符串
    output_data = Column(Text)  # JSON 字符串
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    project = relationship('Project', back_populates='tasks')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'type': self.type,
            'status': self.status,
            'progress': self.progress,
            'input_data': json.loads(self.input_data) if self.input_data else {},
            'output_data': json.loads(self.output_data) if self.output_data else {},
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
```

### 6.4 数据库初始化

#### 6.4.1 初始化脚本示例 (scripts/init_db.py)
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
"""

import sys
from pathlib import Path

# 将项目根目录加入 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.database import engine, Base
from models.project import Project
from models.material import Material
from models.task import Task
from models.ai_model import AIModel
from models.user_setting import UserSetting
from models.operation_log import OperationLog

def init_database():
    """初始化数据库"""
    print('正在创建数据库表...')
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    print('数据库表创建完成')
    
    # 初始化默认数据
    init_default_data()

def init_default_data():
    """初始化默认数据"""
    from config.database import get_db_session
    
    print('正在初始化默认数据...')
    
    with get_db_session() as session:
        # 检查是否已有数据
        existing_settings = session.query(UserSetting).count()
        
        if existing_settings == 0:
            # 创建默认配置
            default_settings = [
                UserSetting(
                    key='default_output_path',
                    value='./output',
                    category='general',
                    description='默认输出路径'
                ),
                UserSetting(
                    key='default_video_quality',
                    value='high',
                    category='video',
                    description='默认视频质量'
                ),
                UserSetting(
                    key='default_audio_quality',
                    value='high',
                    category='audio',
                    description='默认音频质量'
                ),
                UserSetting(
                    key='enable_gpu_acceleration',
                    value='true',
                    category='performance',
                    description='启用 GPU 加速'
                )
            ]
            
            session.add_all(default_settings)
            session.commit()
            
            print('默认配置已创建')
        else:
            print('数据库已存在配置数据，跳过初始化')

def drop_all_tables():
    """删除所有表（慎用）"""
    print('警告：即将删除所有数据库表！')
    confirm = input('确定要继续吗？(yes/no): ')
    
    if confirm.lower() == 'yes':
        Base.metadata.drop_all(bind=engine)
        print('所有表已删除')
    else:
        print('操作已取消')

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库管理工具')
    parser.add_argument('--init', action='store_true', help='初始化数据库')
    parser.add_argument('--drop', action='store_true', help='删除所有表')
    parser.add_argument('--reset', action='store_true', help='重置数据库（删除后重建）')
    
    args = parser.parse_args()
    
    if args.reset:
        drop_all_tables()
        init_database()
    elif args.drop:
        drop_all_tables()
    elif args.init:
        init_database()
    else:
        parser.print_help()
```

---

## 7. AI 模型汇总

### 7.1 模型管理系统

#### 7.1.1 模型配置 (config/models.yaml)
```yaml
# AI 模型配置文件

models:
  # TTS 模型
  tts:
    edge-tts:
      type: tts
      provider: edge
      voices:
        - zh-CN-XiaoxiaoNeural
        - zh-CN-YunxiNeural
        - en-US-AriaNeural
      free: true
      
    coqui-tts:
      type: tts
      provider: coqui
      model_path: resource/models/tts/coqui
      languages: [zh, en, ja, ko]
      quality: high
      
  # ASR 模型
  asr:
    whisper-large-v3:
      type: asr
      provider: openai
      model_path: resource/models/subtitle/Whisper_srt_model
      languages: [zh, en, ja, ko, fr, de, es, ru, ar]
      accuracy: high
      
    funasr-cn:
      type: asr
      provider: alibaba
      model_path: resource/models/subtitle/cn_srt_model
      languages: [zh]
      accuracy: very_high
      fast: true
      
  # 场景检测
  scene_detection:
    transnetv2:
      type: scene
      provider: soCe
      model_path: resource/models/transnetv2-weights
      threshold: 0.3
      
  # 语音活动检测（VAD）
  vad:
    silero-vad:
      type: vad
      provider: silero
      model_path: resource/models/subtitle/vad_model_path
      
  # 说话人识别
  speaker_recognition:
    campplus:
      type: speaker
      provider: alibaba
      model_path: resource/models/subtitle/spk_model_path

# 模型下载源
sources:
  huggingface:
    url: https://huggingface.co
    mirror: https://hf-mirror.com
    
  modelscope:
    url: https://modelscope.cn
    
  github:
    url: https://github.com
```

#### 7.1.2 AI 服务基类 (services/ai_service.py)
```python
import logging
from pathlib import Path
import yaml
from typing import Dict, List, Optional
import torch

logger = logging.getLogger(__name__)

class AIService:
    """AI 服务基类"""
    
    def __init__(self):
        self.config = self._load_config()
        self.device = self._detect_device()
        self.models = {}  # 缓存已加载的模型
        
    def _load_config(self) -> Dict:
        """加载模型配置"""
        config_path = Path(__file__).parent.parent / 'config' / 'models.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _detect_device(self) -> str:
        """检测可用设备"""
        if torch.cuda.is_available():
            device = 'cuda'
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f'检测到 CUDA 设备: {gpu_name}')
        else:
            device = 'cpu'
            logger.info('使用 CPU 进行推理')
        
        return device
    
    def get_model_list(self, model_type: Optional[str] = None) -> List[Dict]:
        """获取模型列表"""
        models = self.config.get('models', {})
        
        result = []
        for type_name, type_models in models.items():
            if model_type and type_name != model_type:
                continue
            
            for model_name, model_config in type_models.items():
                result.append({
                    'id': f'{type_name}_{model_name}',
                    'name': model_name,
                    'type': type_name,
                    'provider': model_config.get('provider', 'unknown'),
                    'path': model_config.get('model_path', ''),
                    'languages': model_config.get('languages', []),
                    'free': model_config.get('free', False),
                    'quality': model_config.get('quality', 'medium')
                })
        
        return result
    
    def get_model_info(self, model_id: str) -> Optional[Dict]:
        """获取模型详细信息"""
        models = self.get_model_list()
        for model in models:
            if model['id'] == model_id:
                return model
        return None
    
    def download_model(self, model_id: str, model_type: str, source: str = 'huggingface'):
        """下载模型（创建后台任务）"""
        from services.task_service import TaskService
        
        task_service = TaskService()
        task_id = task_service.create_task(
            task_type='model_download',
            input_data={
                'model_id': model_id,
                'model_type': model_type,
                'source': source
            }
        )
        
        # 启动下载任务
        task_service.start_model_download_task(task_id)
        
        return task_id
    
    def delete_model(self, model_id: str):
        """删除模型"""
        model_info = self.get_model_info(model_id)
        if not model_info:
            raise ValueError(f'模型不存在: {model_id}')
        
        model_path = Path(model_info['path'])
        if model_path.exists():
            import shutil
            shutil.rmtree(model_path)
            logger.info(f'已删除模型 {model_id}')
        else:
            logger.warning(f'模型路径不存在: {model_path}')
```

### 7.2 TTS 引擎实现

#### 7.2.1 Edge TTS 引擎 (engine/tts_engine.py)
```python
import logging
import asyncio
from pathlib import Path
from typing import Optional, List, Dict
import edge_tts

logger = logging.getLogger(__name__)

class TTSEngine:
    """TTS 引擎"""
    
    def __init__(self):
        self.available_voices = None
    
    async def _get_voices(self) -> List[Dict]:
        """获取可用语音列表"""
        if self.available_voices is None:
            voices = await edge_tts.list_voices()
            self.available_voices = [
                {
                    'name': voice['ShortName'],
                    'gender': voice['Gender'],
                    'locale': voice['Locale'],
                    'display_name': voice['FriendlyName']
                }
                for voice in voices
            ]
        return self.available_voices
    
    def get_voices_sync(self) -> List[Dict]:
        """同步获取语音列表"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._get_voices())
        finally:
            loop.close()
    
    async def _generate_speech(
        self,
        text: str,
        voice: str,
        output_path: str,
        rate: str = '+0%',
        volume: str = '+0%',
        pitch: str = '+0Hz'
    ):
        """生成语音（异步）"""
        logger.info(f'开始生成语音: voice={voice}, text={text[:50]}...')
        
        # 创建 TTS 通信器
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch
        )
        
        # 保存音频
        await communicate.save(output_path)
        
        logger.info(f'语音生成完成: {output_path}')
    
    def generate_speech(
        self,
        text: str,
        voice: str = 'zh-CN-XiaoxiaoNeural',
        output_path: Optional[str] = None,
        speed: float = 1.0,
        volume: float = 1.0,
        pitch: int = 0
    ) -> str:
        """生成语音（同步接口）"""
        # 创建输出路径
        if output_path is None:
            import time
            import uuid
            output_dir = Path('static/make_audios')
            output_dir.mkdir(parents=True, exist_ok=True)
            filename = f'tts_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp3'
            output_path = str(output_dir / filename)
        
        # 转换参数格式
        rate = f'+{int((speed - 1) * 100)}%' if speed >= 1 else f'{int((speed - 1) * 100)}%'
        vol = f'+{int((volume - 1) * 100)}%' if volume >= 1 else f'{int((volume - 1) * 100)}%'
        pitch_str = f'+{pitch}Hz' if pitch >= 0 else f'{pitch}Hz'
        
        # 运行异步任务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                self._generate_speech(
                    text=text,
                    voice=voice,
                    output_path=output_path,
                    rate=rate,
                    volume=vol,
                    pitch=pitch_str
                )
            )
        finally:
            loop.close()
        
        return output_path
    
    def batch_generate(
        self,
        texts: List[str],
        voice: str,
        output_dir: str,
        **kwargs
    ) -> List[str]:
        """批量生成语音"""
        output_paths = []
        
        for i, text in enumerate(texts):
            output_path = Path(output_dir) / f'audio_{i:03d}.mp3'
            output_path = self.generate_speech(
                text=text,
                voice=voice,
                output_path=str(output_path),
                **kwargs
            )
            output_paths.append(output_path)
        
        return output_paths
```

#### 7.2.2 Coqui TTS 引擎（高质量 TTS，可选扩展示例，默认不启用）
```python
import logging
from pathlib import Path
from typing import Optional
import torch
from TTS.api import TTS

logger = logging.getLogger(__name__)

class CoquiTTSEngine:
    """Coqui TTS 引擎（支持多语言高质量 TTS）"""
    
    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        self.model_name = model_name
        self.tts = None
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    def _load_model(self):
        """加载模型"""
        if self.tts is None:
            logger.info(f'加载 Coqui TTS 模型: {self.model_name}')
            self.tts = TTS(self.model_name).to(self.device)
            logger.info('模型加载完成')
    
    def generate_speech(
        self,
        text: str,
        output_path: str,
        language: str = 'zh-cn',
        speaker_wav: Optional[str] = None,  # 参考音频（用于语音克隆）
        **kwargs
    ) -> str:
        """生成语音"""
        self._load_model()
        
        logger.info(f'开始生成语音: language={language}, text={text[:50]}...')
        
        # 生成语音
        if speaker_wav:
            # 使用参考音频进行语音克隆
            self.tts.tts_to_file(
                text=text,
                file_path=output_path,
                speaker_wav=speaker_wav,
                language=language
            )
        else:
            # 使用默认说话人
            self.tts.tts_to_file(
                text=text,
                file_path=output_path,
                language=language
            )
        
        logger.info(f'语音生成完成: {output_path}')
        return output_path
    
    def clone_voice(
        self,
        text: str,
        reference_audio: str,
        output_path: str,
        language: str = 'zh-cn'
    ) -> str:
        """语音克隆"""
        logger.info(f'开始语音克隆: reference={reference_audio}')
        
        return self.generate_speech(
            text=text,
            output_path=output_path,
            language=language,
            speaker_wav=reference_audio
        )
```

### 7.3 ASR 引擎实现

#### 7.3.1 Faster Whisper 引擎 (engine/asr_engine.py)
```python
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from faster_whisper import WhisperModel
import torch

logger = logging.getLogger(__name__)

class ASREngine:
    """ASR（语音识别）引擎"""
    
    def __init__(
        self,
        model_name: str = "large-v3",
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: str = "float16"
    ):
        self.model_name = model_name
        self.model_path = model_path or f"resource/models/subtitle/Whisper_srt_model"
        
        # 自动检测设备
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        # 根据设备调整计算类型
        if self.device == 'cpu':
            compute_type = 'int8'
        
        self.compute_type = compute_type
        self.model = None
    
    def _load_model(self):
        """加载模型"""
        if self.model is None:
            logger.info(f'加载 Whisper 模型: {self.model_name} ({self.device})')
            
            self.model = WhisperModel(
                self.model_path,
                device=self.device,
                compute_type=self.compute_type
            )
            
            logger.info('模型加载完成')
    
    def transcribe(
        self,
        audio_path: str,
        language: str = 'zh',
        initial_prompt: Optional[str] = None,
        word_timestamps: bool = True,
        vad_filter: bool = True
    ) -> Tuple[List[Dict], Dict]:
        """转录音频
        
        Returns:
            segments: 分段列表
            info: 音频信息
        """
        self._load_model()
        
        logger.info(f'开始转录: {audio_path}')
        
        # 转录
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            initial_prompt=initial_prompt,
            word_timestamps=word_timestamps,
            vad_filter=vad_filter
        )
        
        # 转换为列表
        result_segments = []
        for segment in segments:
            seg_dict = {
                'id': segment.id,
                'start': segment.start,
                'end': segment.end,
                'text': segment.text.strip(),
                'words': []
            }
            
            # 添加词级时间戳
            if word_timestamps and segment.words:
                seg_dict['words'] = [
                    {
                        'start': word.start,
                        'end': word.end,
                        'word': word.word,
                        'probability': word.probability
                    }
                    for word in segment.words
                ]
            
            result_segments.append(seg_dict)
        
        info_dict = {
            'language': info.language,
            'language_probability': info.language_probability,
            'duration': info.duration
        }
        
        logger.info(f'转录完成: {len(result_segments)} 个片段')
        
        return result_segments, info_dict
    
    def generate_srt(
        self,
        audio_path: str,
        output_path: Optional[str] = None,
        language: str = 'zh'
    ) -> str:
        """生成 SRT 字幕文件"""
        segments, info = self.transcribe(audio_path, language=language)
        
        if output_path is None:
            output_path = Path(audio_path).with_suffix('.srt')
        
        # 写入 SRT 文件
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(segments, 1):
                # 序号
                f.write(f'{i}\n')
                
                # 时间戳
                start_time = self._format_timestamp(seg['start'])
                end_time = self._format_timestamp(seg['end'])
                f.write(f'{start_time} --> {end_time}\n')
                
                # 文本
                f.write(f'{seg["text"]}\n\n')
        
        logger.info(f'SRT 字幕已保存: {output_path}')
        return str(output_path)
    
    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """将时间秒数格式化为 SRT 时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        
        return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'
```

#### 7.3.2 FunASR 引擎（阿里巴巴中文 ASR 优化）（可选扩展示例，默认不启用）
```python
import logging
from pathlib import Path
from typing import List, Dict
from funasr import AutoModel

logger = logging.getLogger(__name__)

class FunASREngine:
    """FunASR 引擎（阿里巴巴中文 ASR，集成 VAD / 标点 / 说话人识别）"""
    
    def __init__(self, model_path: str = "resource/models/subtitle/cn_srt_model"):
        self.model_path = model_path
        self.model = None
    
    def _load_model(self):
        """加载模型"""
        if self.model is None:
            logger.info(f'加载 FunASR 模型: {self.model_path}')
            
            self.model = AutoModel(
                model=self.model_path,
                vad_model="fsmn-vad",
                punc_model="ct-punc",
                spk_model="cam++"
            )
            
            logger.info('模型加载完成')
    
    def transcribe(
        self,
        audio_path: str,
        hotword: str = ""
    ) -> List[Dict]:
        """转录音频"""
        self._load_model()
        
        logger.info(f'开始转录（FunASR）: {audio_path}')
        
        # 转录
        result = self.model.generate(
            input=audio_path,
            hotword=hotword,
            batch_size_s=300  # 批处理时长（秒）
        )
        
        # 解析结果
        segments = []
        for item in result:
            segments.append({
                'text': item['text'],
                'timestamp': item.get('timestamp', []),
                'speaker': item.get('speaker', None)
            })
        
        logger.info(f'转录完成: {len(segments)} 个片段')
        
        return segments
```

### 7.4 场景检测引擎（可选扩展示例，默认不启用）

#### 7.4.1 TransNetV2 场景检测 (engine/scene_detect.py)
```python
import logging
from pathlib import Path
from typing import List, Dict

## 8. 视频处理引擎

### 8.1 FFmpeg 引擎封装

#### 8.1.1 FFmpeg 引擎基类 (engine/ffmpeg_engine.py)
```python
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import os

logger = logging.getLogger(__name__)

class FFmpegEngine:
    """FFmpeg 处理引擎"""
    
    def __init__(self, ffmpeg_path: str = 'ffmpeg.exe'):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = 'ffprobe.exe'
        
        # 检查 FFmpeg 是否可用
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """检查 FFmpeg 是否可用"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info('FFmpeg 可用')
            else:
                raise RuntimeError('FFmpeg 不可用')
        except Exception as e:
            logger.error(f'FFmpeg 检查失败: {e}')
            raise
    
    def get_video_info(self, video_path: str) -> Dict:
        """获取视频信息"""
        cmd = [
            self.ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f'获取视频信息失败: {result.stderr}')
            
            info = json.loads(result.stdout)
            
            # 提取关键信息
            video_stream = next(
                (s for s in info['streams'] if s['codec_type'] == 'video'),
                None
            )
            audio_stream = next(
                (s for s in info['streams'] if s['codec_type'] == 'audio'),
                None
            )
            
            return {
                'duration': float(info['format']['duration']),
                'size': int(info['format']['size']),
                'bitrate': int(info['format']['bit_rate']),
                'format': info['format']['format_name'],
                'video': {
                    'codec': video_stream['codec_name'] if video_stream else None,
                    'width': video_stream['width'] if video_stream else None,
                    'height': video_stream['height'] if video_stream else None,
                    'fps': eval(video_stream['r_frame_rate']) if video_stream else None
                } if video_stream else None,
                'audio': {
                    'codec': audio_stream['codec_name'] if audio_stream else None,
                    'sample_rate': int(audio_stream['sample_rate']) if audio_stream else None,
                    'channels': audio_stream['channels'] if audio_stream else None
                } if audio_stream else None
            }
        except Exception as e:
            logger.error(f'获取视频信息失败: {e}')
            raise
    
    def cut_video(
        self,
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
        copy_codec: bool = True
    ):
        """剪辑视频"""
        logger.info(f'剪辑视频: {start_time}s -> {end_time}s')
        
        cmd = [
            self.ffmpeg_path,
            '-i', input_path,
            '-ss', str(start_time),
            '-to', str(end_time),
            '-y'  # 覆盖输出文件
        ]
        
        if copy_codec:
            # 复制编码（速度快）
            cmd.extend(['-c', 'copy'])
        else:
            # 重新编码（兼容性更好）
            cmd.extend([
                '-c:v', 'libx264',
                '-c:a', 'aac'
            ])
        
        cmd.append(output_path)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise RuntimeError(f'剪辑失败: {result.stderr}')
            
            logger.info(f'剪辑完成: {output_path}')
        except Exception as e:
            logger.error(f'剪辑失败: {e}')
            raise
    
    def merge_videos(
        self,
        input_paths: List[str],
        output_path: str,
        transition_duration: float = 0.5
    ):
        """合并视频"""
        logger.info(f'合并 {len(input_paths)} 个视频')
        
        # 创建 concat 文件
        concat_file = Path(output_path).with_suffix('.txt')
        with open(concat_file, 'w', encoding='utf-8') as f:
            for path in input_paths:
                f.write(f"file '{path}'\n")
        
        cmd = [
            self.ffmpeg_path,
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-c', 'copy',
            '-y',
            output_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                raise RuntimeError(f'合并失败: {result.stderr}')
            
            logger.info(f'合并完成: {output_path}')
            
            # 删除临时文件
            concat_file.unlink()
        except Exception as e:
            logger.error(f'合并失败: {e}')
            raise
    
    def add_audio_to_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        mix_mode: str = 'replace',  # replace/mix
        audio_volume: float = 1.0,
        video_volume: float = 0.3
    ):
        """为视频添加音频"""
        logger.info(f'为视频添加音频: mode={mix_mode}')
        
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-i', audio_path
        ]
        
        if mix_mode == 'replace':
            # 替换音频
            cmd.extend([
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest'
            ])
        else:
            # 混合音频
            cmd.extend([
                '-filter_complex',
                f'[0:a]volume={video_volume}[a1];[1:a]volume={audio_volume}[a2];[a1][a2]amix=inputs=2[a]',
                '-map', '0:v',
                '-map', '[a]',
                '-c:v', 'copy',
                '-c:a', 'aac'
            ])
        
        cmd.extend(['-y', output_path])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                raise RuntimeError(f'添加音频失败: {result.stderr}')
            
            logger.info(f'音频添加完成: {output_path}')
        except Exception as e:
            logger.error(f'添加音频失败: {e}')
            raise
    
    def extract_audio(
        self,
        video_path: str,
        output_path: str,
        audio_codec: str = 'mp3',
        bitrate: str = '192k'
    ):
        """提取音频"""
        logger.info(f'提取音频: {video_path}')
        
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-vn',  # 不处理视频流
            '-acodec', audio_codec,
            '-ab', bitrate,
            '-y',
            output_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise RuntimeError(f'提取音频失败: {result.stderr}')
            
            logger.info(f'音频提取完成: {output_path}')
        except Exception as e:
            logger.error(f'提取音频失败: {e}')
            raise
    
    def add_subtitle(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        subtitle_style: Optional[Dict] = None
    ):
        """添加字幕"""
        logger.info(f'添加字幕: {subtitle_path}')
        
        # 默认字幕样式
        if subtitle_style is None:
            subtitle_style = {
                'FontName': 'Arial',
                'FontSize': 24,
                'PrimaryColour': '&H00FFFFFF',
                'OutlineColour': '&H00000000',
                'Outline': 2
            }
        
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-vf', f"subtitles={subtitle_path}",
            '-c:a', 'copy',
            '-y',
            output_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                raise RuntimeError(f'添加字幕失败: {result.stderr}')
            
            logger.info(f'字幕添加完成: {output_path}')
        except Exception as e:
            logger.error(f'添加字幕失败: {e}')
            raise
```

---

*继续下一部分...*



