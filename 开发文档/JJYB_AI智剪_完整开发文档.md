# AIJian - 完整开发文档

**版本**: 2.0  
**更新日期**: 2025-11-08  
**目标**: 系统性说明 AIJian 智能视频剪辑工具的架构设计与实现细节

---

## 📑 目录

1. [项目概述](#1-项目概述)
2. [系统架构设计](#2-系统架构设计)
3. [技术栈说明](#3-技术栈说明)
4. [前端设计](#4-前端设计)
5. [后端设计](#5-后端设计)
6. [数据库设计](#6-数据库设计)
7. [AI 模型汇总](#7-ai-模型汇总)
8. [视频处理引擎](#8-视频处理引擎)
9. [核心功能模块](#9-核心功能模块)
10. [API 接口设计](#10-api-接口设计)
11. [部署与打包](#11-部署与打包)
12. [开发路线图](#12-开发路线图)
13. [性能优化](#13-性能优化)
14. [安全策略](#14-安全策略)
15. [测试策略](#15-测试策略)

---

## 1. 项目概述

### 1.1 项目简介

AIJian 是一款基于 AI 技术的桌面端智能视频剪辑工具，采用 **Flask + PyWebView** 架构，提供 Web 化的用户界面和本地运行的后端服务。

### 1.2 核心卖点

- **AI 驱动**: 集成多种 AI 模型，实现智能化视频处理
- **开箱即用**: 内置 Python 运行环境，无需复杂额外配置
- **跨平台**: 基于 Web 技术，便于扩展到多平台
- **现代 UI**: 响应式界面设计，用户体验友好
- **高度集成**: FFmpeg、ImageMagick 等专业工具无缝集成

### 1.3 核心功能

1. **智能配音与文案生成**
   - AI 文案方案生成
   - TTS 语音合成
   - 多语言、多风格支持
   - 音频混合与音量压制

2. **智能视频剪辑**
   - 场景检测与分割
   - 关键帧提取
   - 自动转场
   - 节奏匹配剪辑

3. **混剪与特效**
   - 多轨素材混剪
   - 智能转场与布局
   - 音视频同步
   - 特效与滤镜添加

4. **AI 内容审核**
   - 情感/敏感内容检测
   - 场景与镜头分析
   - 违规标签标记
   - 审核报告生成

5. **项目管理**
   - 项目 CRUD 管理
   - 模板系统与预设
   - 批量任务处理
   - 版本记录与回溯

---

## 2. 系统架构设计

### 2.1 整体架构

 ```
整体架构自上而下分为五层：

1. 用户界面层（UI Layer）
   - PyWebView 桌面窗口
   - Web 前端：HTML / CSS / JavaScript
   - 主要职责：为用户提供可视化操作界面，收集用户输入并展示处理结果

2. Web 应用层（Web Application Layer）
   - Flask Web 应用
   - HTTP / WebSocket 接口
   - 路由控制器（Routes）、中间件（Middleware）、WebSocket 服务（实时通信）
   - 主要职责：接收前端请求、进行基础校验和路由分发，并向业务层发起调用

3. 业务逻辑层（Business Layer）
   - 视频服务（Video Service）
   - 音频服务（Audio Service）
   - AI 服务（AI Service）
   - 项目管理服务（Project Service）
   - 主要职责：封装各类业务规则和处理流程，对下屏蔽底层实现细节，对上提供统一接口

4. 数据访问层（Data Access Layer）
   - 文件存储（Files）：项目文件、素材、导出结果
   - 配置管理（Config）：INI / YAML 等配置
   - 日志系统（Log）：运行日志、错误日志
   - 缓存管理（Cache）：Redis / 内存缓存
   - 主要职责：负责数据的持久化与读取，为业务层提供统一的数据访问接口

5. 基础设施层（Infrastructure Layer）
   - 多媒体处理工具：FFmpeg、ImageMagick 等
   - AI 运行时：ONNX Runtime / PyTorch 等
   - 数据库：SQLite / PostgreSQL / MySQL 等
   - 文件系统：本地磁盘 / 网络存储
   - 主要职责：提供通用的系统能力和基础依赖，为上层所有模块提供支撑
 ```

### 2.2 技术栈分层

#### 2.2.1 表现层 (Presentation Layer)
- **PyWebView**: 桌面窗口容器
- **HTML5/CSS3**: 页面结构与样式
- **JavaScript (ES6+)**: 前端交互逻辑
- **Layui/Bootstrap**: UI 组件库
- **Socket.IO**: 实时通信

#### 2.2.2 应用层 (Application Layer)
- **Flask**: Web 框架
- **Flask-SocketIO**: WebSocket 支持
- **Flask-CORS**: 跨域处理
- **Jinja2**: 模板引擎

#### 2.2.3 业务层 (Business Layer)
- **视频处理服务**: 剪辑、合成、转码
- **音频处理服务**: TTS、配音、降噪
- **AI 推理服务**: 模型加载、推理与后处理
- **项目管理服务**: 项目 CRUD、版本管理

#### 2.2.4 数据层 (Data Layer)
- **文件存储**: 项目文件、素材、导出结果
- **配置管理**: INI 配置文件
- **日志系统**: 运行日志与错误日志
- **缓存系统**: Redis / 内存缓存

#### 2.2.5 基础设施层 (Infrastructure Layer)
- **FFmpeg**: 音视频处理
- **ImageMagick**: 图像处理
- **Rubberband**: 音频变速变调
- **AI Runtime**: ONNX / PyTorch 推理框架

### 2.3 进程架构

```
主进程（Main Process）
├── Flask Web Server（后端服务进程）
│   ├── Request Handler Threads（请求处理线程）
│   ├── WebSocket Handler（WebSocket 事件处理）
│   └── Task Queue Workers（任务队列工作线程）
├── PyWebView GUI（主线程）
│   └── 浏览器内嵌渲染（前端页面运行环境）
├── FFmpeg 子进程
│   └── 视频处理任务（转码 / 剪辑 / 合成等）
├── AI 推理进程
│   ├── TTS 模型推理
│   ├── ASR 模型推理
│   └── 场景识别模型推理
└── 后台任务进程
    ├── 文件监控
    ├── 缓存清理
    └── 日志轮转
```

### 2.4 数据流设计

```
用户操作
↓
前端事件触发（按钮点击 / 表单提交 / 拖拽操作等）
↓
AJAX / Fetch 请求 → Flask 路由处理
↓
业务服务处理
    - 文件 I/O 操作
    - FFmpeg 调用
    - AI 模型推理
    - 数据库操作
↓
返回 JSON 响应
↓
前端更新 UI
↓
WebSocket 实时推送进度（实时状态 / 进度条 / 日志）
```

---

## 3. 技术栈说明

### 3.1 后端技术栈

#### 3.1.1 基础框架
```python
# requirements.txt
Flask==3.0.0              # Web 框架
flask-cors==4.0.0         # 跨域支持
flask-socketio==5.3.5     # WebSocket 支持
python-socketio==5.10.0   # Socket.IO 客户端
```

#### 3.1.2 Web 服务器
```python
# 开发环境
werkzeug==3.0.1          # Flask 内置开发服务器

# 生产环境推荐
gunicorn==21.2.0         # WSGI HTTP 服务器
gevent==23.9.1           # 协程/并发支持
gevent-websocket==0.10.1 # WebSocket 支持
```

#### 3.1.3 GUI 框架
```python
pywebview==4.4.1         # 桌面 GUI 容器
pythonnet==3.0.3         # 与 .NET 互操作（Windows）
```

#### 3.1.4 视频处理
```python
# FFmpeg Python 绑定
av==11.0.0               # PyAV（FFmpeg 封装）
ffmpeg-python==0.2.0     # FFmpeg 命令行封装

# 或直接调用 FFmpeg 可执行文件
# ffmpeg.exe, ffprobe.exe, ffplay.exe
```

#### 3.1.5 图像处理
```python
Pillow==10.1.0           # PIL 图像处理
opencv-python==4.8.1     # OpenCV 计算机视觉
imagemagick==1.2.0       # ImageMagick Python 绑定
```

#### 3.1.6 音频处理
```python
pydub==0.25.1            # 音频处理库
librosa==0.10.1          # 音频分析
soundfile==0.12.1        # 音频文件 I/O
scipy==1.11.4            # 科学计算（滤波等音频处理）
```

### 3.2 AI/ML 技术栈

#### 3.2.1 深度学习框架
```python
torch==2.1.1             # PyTorch
torchvision==0.16.1      # 视觉模型
torchaudio==2.1.1        # 音频模型
onnxruntime==1.16.3      # ONNX 推理引擎
onnxruntime-gpu==1.16.3  # GPU 加速版本
```

#### 3.2.2 语音识别 (ASR)
```python
faster-whisper==1.0.0    # Whisper ASR 优化版本
openai-whisper==20231117 # OpenAI Whisper
funasr==1.0.0            # FunASR（中文优化，可选扩展，默认不启用）
```

#### 3.2.3 语音合成 (TTS)
```python
edge-tts==6.1.10         # Edge TTS（在线 TTS 服务）
pyttsx3==2.90            # 本地 TTS 引擎
TTS==0.22.0              # Coqui TTS（高质量，可选扩展，本项目默认不启用）
```

#### 3.2.4 NLP 处理
```python
transformers==4.35.2     # HuggingFace Transformers
sentencepiece==0.1.99    # Tokenizer
jieba==0.42.1            # 中文分词
```

#### 3.2.5 计算机视觉
```python
# 场景检测
scenedetect==0.6.2       # PySceneDetect
transnetv2==0.1.0        # TransNetV2 场景切分（深度模型扩展，默认不启用）

# 目标检测
ultralytics==8.0.220     # YOLOv8
```

#### 3.2.6 模型工具
```python
huggingface-hub==0.19.4  # 模型下载与管理
modelscope==1.10.0       # 魔搭 ModelScope 模型
safetensors==0.4.1       # 更安全的权重文件格式
```

### 3.3 前端技术栈

#### 3.3.1 基础库
```javascript
// 基础库
jquery@3.6.4             // jQuery
lodash@4.17.21           // 工具函数库

// UI 框架
layui@2.8.12             // Layui UI 框架
bootstrap@5.3.0          // Bootstrap（可选）

// 实时通信
socket.io-client@4.5.4   // Socket.IO 客户端

// 视频播放
plyr@3.7.8               // Plyr 视频播放器

// 工具库
sortablejs@1.15.0        // 拖拽排序
axios@1.6.2              // HTTP 客户端
dayjs@1.11.10            // 日期处理
```

#### 3.3.2 CSS 框架
```css
/* Layui CSS */
layui.css

/* 自定义样式 */
index.css
style.css

/* 图标字体 */
iconfont
```

#### 3.3.3 前端构建工具（可选）
```json
{
  "devDependencies": {
    "webpack": "^5.89.0",
    "babel": "^7.23.5",
    "sass": "^1.69.5",
    "terser": "^5.26.0"
  }
}
```

### 3.4 数据库技术栈

#### 3.4.1 关系型数据库（推荐）
```python
# SQLite（轻量级，适合单机场景）
sqlite3                  # Python 内置 SQLite 支持

# 使用 ORM / 生产环境数据库（可选扩展方案）
SQLAlchemy==2.0.23       # ORM 框架（用于抽象数据库访问层）
alembic==1.13.0          # 数据库迁移工具（可选）

# PostgreSQL（生产环境推荐，可作为最终部署方案）
psycopg2-binary==2.9.9   # PostgreSQL 驱动（支持多用户并发连接）

# MySQL（可选，可作为扩展）
pymysql==1.1.0           # MySQL 驱动（可选）
```

#### 3.4.2 NoSQL 数据库（可选）
```python
# Redis（缓存和任务队列），可与 Celery 搭配使用；
# 当前项目中仅作为后续扩展的预留方案。
redis==5.0.1             # Redis 客户端（可选/扩展）
hiredis==2.3.2           # Redis 高性能解析器（可选）

# MongoDB（文档型存储，可选），适合后续大数据量扩展场景
pymongo==4.6.0           # MongoDB 驱动（可选）
```

### 3.5 工具库

#### 3.5.1 文件处理
```python
pathlib                  # 路径处理（标准库）
shutil                   # 文件操作（标准库）
watchdog==3.0.0          # 文件监控
```

#### 3.5.2 配置管理
```python
configparser             # INI 配置（标准库）
python-dotenv==1.0.0     # 环境变量管理
pyyaml==6.0.1            # YAML 配置
```

#### 3.5.3 日志处理
```python
logging                  # 日志模块（标准库）
loguru==0.7.2            # 更友好的日志库
```

#### 3.5.4 任务队列
```python
# 如需对项目的异步任务队列做更完整的工程化支持，可参考：
# - 使用 Celery + Redis 搭建分布式任务队列
# - 将本段文档进一步细化为运维/部署说明
# 当前实现：通过 backend/services/task_service.py
#   + backend/database/db_manager.py + Flask-SocketIO + 若干工作线程
# 实现了一个基础的内置任务队列。

celery==5.3.4            # 分布式任务队列（可选/扩展）
redis==5.0.1             # Celery 消息代理（可选）
flower==2.0.1            # Celery 监控工具（可选）
```

#### 3.5.5 进程管理
```python
psutil==5.9.6            # 进程和系统监控
multiprocessing          # 多进程（标准库）
threading                # 多线程（标准库）
```

#### 3.5.6 HTTP 客户端
```python
requests==2.31.0         # HTTP 请求库
httpx==0.25.2            # 异步 HTTP 客户端
aiohttp==3.9.1           # 异步 HTTP 框架
```

### 3.6 开发工具

#### 3.6.1 代码质量
```python
# 代码格式化
black==23.12.0           # 代码格式化
isort==5.13.2            # 导入排序
autopep8==2.0.4          # PEP8 格式化

# 代码检查
pylint==3.0.3            # 代码静态检查
flake8==6.1.0            # 风格检查
mypy==1.7.1              # 类型检查
```

#### 3.6.2 测试工具
```python
pytest==7.4.3            # 测试框架
pytest-cov==4.1.0        # 覆盖率统计
pytest-mock==3.12.0      # Mock 测试
```

#### 3.6.3 打包工具
```python
# Windows 打包
pyinstaller==6.3.0       # Python 打包工具
nuitka==1.9.6            # Python 编译器

# 安装包制作
innosetup                # Windows 安装包（外部工具）
```

---

## 4. 前端设计

### 4.1 项目结构

```
frontend/
├── app.py                       # 前端 Flask 应用入口
├── templates/                   # HTML 模板
│   ├── base.html               # 基础布局模板
│   ├── index.html              # 视频编辑器首页
│   ├── commentary.html         # 原创解说页面
│   ├── remix.html              # 混剪模式页面
│   ├── voiceover.html          # AI 配音页面
│   ├── settings.html           # 设置与 API 配置页面
│   ├── projects.html           # 项目管理页面
│   ├── materials.html          # 素材管理页面
│   ├── mode_select.html        # 模式选择页面
│   ├── ai_features.html        # AI 功能总览/诊断页面
│   ├── diagnostic.html         # 系统诊断页面
│   ├── home.html               # 首页入口/说明页面
│   ├── voice_clone.html        # 语音克隆配置页面
│   ├── voice_config.html       # 全局配音配置页面
│   ├── 404.html                # 404 错误页
│   └── 500.html                # 500 错误页
└── static/                     # 静态资源
    ├── css/                   # 样式表（按需扩展）
    ├── img/                   # 图片资源
    ├── font/                  # 字体文件
    └── js/                    # 前端脚本
        ├── common.js          # 通用交互逻辑与工具函数
        ├── editor-fixes.js    # 编辑器兼容性与兜底修复脚本
        └── page-transition.js # 页面切换与动效脚本
```

### 4.2 页面结构

#### 4.2.1 基础模板 (template.html)
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}AIJian{% endblock %}</title>
    
    <!-- CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='desktop/style/layui.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='desktop/style/index.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='desktop/plyr/plyr.min.css') }}">
    
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- 页面内容 -->
    {% block content %}{% endblock %}
    
    <!-- JavaScript -->
    <script src="{{ url_for('static', filename='desktop/javascript/layui.js') }}"></script>
    <script src="{{ url_for('static', filename='desktop/javascript/socket.io.js') }}"></script>
    <script src="{{ url_for('static', filename='desktop/javascript/tools.js') }}"></script>
    
    {% block extra_js %}{% endblock %}
</body>
</html>
```

#### 4.2.2 首页布局 (index.html)
```html
{% extends "template.html" %}
{% block title %}AIJian - 智能视频剪辑工具{% endblock %}

{% block content %}
<div class="layui-layout layui-layout-admin">
    <!-- 顶部导航 -->
    <div class="layui-header">
        <div class="layui-logo">AIJian</div>
        <ul class="layui-nav layui-layout-right">
            <li class="layui-nav-item">
                <a id="vip_type">开源 + 赞助版</a>
            </li>
        </ul>
    </div>
    
    <!-- 左侧菜单 -->
    <div class="layui-side layui-bg-black">
        <div class="layui-side-scroll">
            <ul class="layui-nav layui-nav-tree">
                <li class="layui-nav-item layui-this">
                    <a onclick="clicklist('index')">
                        <i class="layui-icon layui-icon-home"></i>首页
                    </a>
                </li>
                <li class="layui-nav-item">
                    <a onclick="clicklist('make-audio')">
                        <i class="layui-icon layui-icon-headset"></i>智能文案/配音
                    </a>
                </li>
                <li class="layui-nav-item">
                    <a><i class="layui-icon layui-icon-util"></i>智能解说/混剪</a>
                    <dl class="layui-nav-child">
                        <dd><a onclick="clicklist('commentary-cut-slim')">原创解说剪辑</a></dd>
                        <dd><a onclick="clicklist('mixed-cut-slim')">原创混剪模式</a></dd>
                    </dl>
                </li>
                <li class="layui-nav-item">
                    <a onclick="clicklist('models-list')">
                        <i class="layui-icon layui-icon-bot"></i>模型管理
                    </a>
                </li>
                <li class="layui-nav-item">
                    <a onclick="clicklist('setting')">
                        <i class="layui-icon layui-icon-set-fill"></i>设置
                    </a>
                </li>
            </ul>
        </div>
    </div>
    
    <!-- 主体内容区 -->
    <div class="layui-body">
        <div style="padding: 15px;">
            <!-- 动态内容区域 -->
            <div id="index_content">
                <!-- 项目列表 -->
            </div>
            <div id="make-audio" style="display: none">
                <!-- 音频生成页面 -->
            </div>
            <div id="commentary-cut-slim" style="display: none">
                <!-- 解说剪辑页面 -->
            </div>
            <div id="mixed-cut-slim" style="display: none">
                <!-- 混剪页面 -->
            </div>
            <div id="setting" style="display: none">
                {% include 'index_son/setting.html' %}
            </div>
            <div id="models-list" style="display: none">
                {% include 'index_son/model_set.html' %}
            </div>
        </div>
    </div>
    
    <!-- 底部信息 -->
    <div class="layui-footer">
        AIJian v2.0 - 开源 + 赞助版
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{{ url_for('static', filename='desktop/javascript/index.js') }}"></script>
{% endblock %}
```

### 4.3 核心前端功能

#### 4.3.1 页面路由管理 (index.js)
```javascript
// 页面切换
function clicklist(pageName) {
    // 隐藏所有页面
    document.querySelectorAll('.layui-body > div > div[id]').forEach(el => {
        el.style.display = 'none';
    });
    
    // 显示目标页面
    const targetPage = document.getElementById(pageName);
    if (targetPage) {
        targetPage.style.display = 'block';
    }
    
    // 加载页面数据
    loadPageData(pageName);
    
    // 更新 URL（可选，使用 History API）
    history.pushState({page: pageName}, '', `#${pageName}`);
}

// 加载页面数据
function loadPageData(pageName) {
    switch(pageName) {
        case 'index':
            loadProjects();
            break;
        case 'make-audio':
            initAudioPage();
            break;
        case 'commentary-cut-slim':
            initCommentaryPage();
            break;
        case 'mixed-cut-slim':
            initMixedCutPage();
            break;
        case 'models-list':
            loadModels();
            break;
        default:
            break;
    }
}

// 浏览器返回按钮处理
window.addEventListener('popstate', (event) => {
    if (event.state && event.state.page) {
        clicklist(event.state.page);
    }
});
```

#### 4.3.2 API 请求封装 (tools.js)
```javascript
// API 基础 URL
const API_BASE_URL = 'http://127.0.0.1:5000/api';

// 通用请求函数
async function apiRequest(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        const result = await response.json();
        
        if (result.code === 0) {
            return result.data;
        } else {
            throw new Error(result.msg || '请求失败');
        }
    } catch (error) {
        console.error('API 请求错误:', error);
        layui.layer.msg('请求失败: ' + error.message, {icon: 2});
        throw error;
    }
}

// 辅助方法
const api = {
    get: (endpoint) => apiRequest(endpoint, 'GET'),
    post: (endpoint, data) => apiRequest(endpoint, 'POST', data),
    put: (endpoint, data) => apiRequest(endpoint, 'PUT', data),
    delete: (endpoint) => apiRequest(endpoint, 'DELETE'),
};

// 文件上传
async function uploadFile(file, onProgress) {
    const formData = new FormData();
    formData.append('file', file);
    
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        // 上传进度监听
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable && onProgress) {
                const percent = Math.round((e.loaded / e.total) * 100);
                onProgress(percent);
            }
        });
        
        // 上传完成回调
        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                const result = JSON.parse(xhr.responseText);
                if (result.code === 0) {
                    resolve(result.data);
                } else {
                    reject(new Error(result.msg));
                }
            } else {
                reject(new Error('上传失败'));
            }
        });
        
        xhr.addEventListener('error', () => reject(new Error('网络错误')));
        
        xhr.open('POST', `${API_BASE_URL}/upload`);
        xhr.send(formData);
    });
}
```

#### 4.3.3 WebSocket 实时通信
```javascript
// Socket.IO 连接
const socket = io('http://127.0.0.1:5000', {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5
});

// 连接成功
socket.on('connect', () => {
    console.log('WebSocket 已连接');
    layui.layer.msg('实时连接已建立', {icon: 1, time: 1000});
});

// 连接断开
socket.on('disconnect', () => {
    console.log('WebSocket 已断开');
    layui.layer.msg('连接已断开', {icon: 2, time: 2000});
});

// 处理进度更新
socket.on('task_progress', (data) => {
    updateProgressBar(data.task_id, data.progress, data.status);
});

// 处理任务完成
socket.on('task_complete', (data) => {
    layui.layer.msg('任务已完成', {icon: 1});
    onTaskComplete(data.task_id, data.result);
});

// 处理错误
socket.on('task_error', (data) => {
    layui.layer.msg('任务失败: ' + data.error, {icon: 2});
    onTaskError(data.task_id, data.error);
});

// 发送任务请求
function startTask(taskType, taskData) {
    const taskId = generateTaskId();
    socket.emit('start_task', {
        task_id: taskId,
        task_type: taskType,
        data: taskData
    });
    return taskId;
}

// 生成任务 ID
function generateTaskId() {
    return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
```

#### 4.3.4 进度条组件
```javascript
// 创建进度条
function createProgressBar(taskId, container) {
    const progressHtml = `
        <div class="progress-container" id="progress_${taskId}">
            <div class="progress-header">
                <span class="progress-label">处理中...</span>
                <span class="progress-percent">0%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: 0%"></div>
            </div>
            <div class="progress-footer">
                <span class="progress-status">准备中</span>
                <button class="layui-btn layui-btn-xs layui-btn-danger" onclick="cancelTask('${taskId}')">
                    取消
                </button>
            </div>
        </div>
    `;
    
    $(container).append(progressHtml);
}

// 更新进度条
function updateProgressBar(taskId, progress, status) {
    const progressEl = $(`#progress_${taskId}`);
    if (progressEl.length === 0) return;
    
    // 更新进度百分比
    progressEl.find('.progress-fill').css('width', `${progress}%`);
    progressEl.find('.progress-percent').text(`${progress}%`);
    
    // 更新状态文本
    progressEl.find('.progress-status').text(status);
    
    // 完成时修改样式
    if (progress >= 100) {
        progressEl.find('.progress-fill').addClass('complete');
        progressEl.find('.progress-label').text('处理完成');
    }
}

// 取消任务
function cancelTask(taskId) {
    layui.layer.confirm('确定要取消任务吗？', {
        btn: ['确定', '取消']
    }, function(index) {
        socket.emit('cancel_task', {task_id: taskId});
        layui.layer.close(index);
        $(`#progress_${taskId}`).fadeOut(300, function() {
            $(this).remove();
        });
    });
}
```

### 4.4 CSS 样式设计

#### 4.4.1 主题变量 (style.css)
```css
:root {
    /* 主题颜色 */
    --primary-color: #009688;
    --secondary-color: #5FB878;
    --danger-color: #FF5722;
    --warning-color: #FFB800;
    --info-color: #01AAED;
    
    /* 文字颜色 */
    --text-primary: #333333;
    --text-secondary: #666666;
    --text-disabled: #999999;
    
    /* 背景颜色 */
    --bg-light: #F8F8F8;
    --bg-white: #FFFFFF;
    --bg-dark: #23262E;
    
    /* 边框颜色 */
    --border-color: #E6E6E6;
    --border-radius: 4px;
    
    /* 阴影 */
    --shadow-sm: 0 2px 4px rgba(0,0,0,0.08);
    --shadow-md: 0 4px 8px rgba(0,0,0,0.12);
    --shadow-lg: 0 8px 16px rgba(0,0,0,0.16);
    
    /* 间距 */
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 16px;
    --spacing-lg: 24px;
    --spacing-xl: 32px;
}
```

#### 4.4.2 布局样式
```css
/* 主体布局 */
.layui-layout-admin {
    min-height: 100vh;
}

/* 顶部导航 */
.layui-header {
    background-color: var(--bg-dark);
    box-shadow: var(--shadow-md);
    z-index: 1000;
}

.layui-logo {
    font-size: 20px;
    font-weight: bold;
    color: var(--primary-color);
    padding: 0 20px;
}

/* 左侧菜单 */
.layui-side {
    width: 220px;
    box-shadow: var(--shadow-sm);
}

.layui-nav-tree {
    width: 220px;
}

.layui-nav-item a {
    transition: all 0.3s;
}

.layui-nav-item a:hover {
    background-color: rgba(0, 150, 136, 0.1);
}

/* 主体内容区 */
.layui-body {
    left: 220px;
    background-color: var(--bg-light);
}

/* 底部信息 */
.layui-footer {
    background-color: var(--bg-white);
    border-top: 1px solid var(--border-color);
    text-align: center;
    color: var(--text-secondary);
}
```

#### 4.4.3 组件样式
```css
/* 卡片样式 */
.card {
    background: var(--bg-white);
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-sm);
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-md);
    transition: all 0.3s;
}

.card:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
}

/* 项目卡片 */
.project-card {
    position: relative;
    width: 280px;
    height: 200px;
    cursor: pointer;
    overflow: hidden;
}

.project-card-image {
    width: 100%;
    height: 140px;
    object-fit: cover;
    transition: transform 0.3s;
}

.project-card:hover .project-card-image {
    transform: scale(1.05);
}

.project-card-info {
    padding: var(--spacing-sm);
}

.project-card-title {
    font-size: 16px;
    font-weight: bold;
    color: var(--text-primary);
    margin-bottom: var(--spacing-xs);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.project-card-meta {
    font-size: 12px;
    color: var(--text-secondary);
}

/* 进度条样式 */
.progress-container {
    background: var(--bg-white);
    border-radius: var(--border-radius);
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-md);
    box-shadow: var(--shadow-sm);
}

.progress-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--spacing-sm);
}

.progress-label {
    font-weight: bold;
    color: var(--text-primary);
}

.progress-percent {
    color: var(--primary-color);
    font-weight: bold;
}

.progress-bar {
    height: 20px;
    background: var(--bg-light);
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: var(--spacing-sm);
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
    transition: width 0.3s ease;
    border-radius: 10px;
}

.progress-fill.complete {
    background: var(--secondary-color);
}

.progress-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.progress-status {
    font-size: 12px;
    color: var(--text-secondary);
}

/* 按钮样式 */
.btn-group {
    display: flex;
    gap: var(--spacing-sm);
}

.btn-icon {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
}

/* 表单样式 */
.form-group {
    margin-bottom: var(--spacing-md);
}

.form-label {
    display: block;
    margin-bottom: var(--spacing-xs);
    font-weight: bold;
    color: var(--text-primary);
}

.form-control {
    width: 100%;
    padding: var(--spacing-sm);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    font-size: 14px;
    transition: border-color 0.3s;
}

.form-control:focus {
    border-color: var(--primary-color);
    outline: none;
    box-shadow: 0 0 0 2px rgba(0, 150, 136, 0.1);
}

/* 响应式设计 */
@media screen and (max-width: 768px) {
    .layui-side {
        width: 180px;
    }
    
    .layui-body {
        left: 180px;
    }
    
    .project-card {
        width: 100%;
    }
}
```

### 4.5 响应式设计

#### 4.5.1 移动端适配
```javascript
// 检测设备类型
function isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

// 根据设备加载不同页面
if (isMobile()) {
    window.location.href = '/mob';  // 加载移动端页面
}
```

#### 4.5.2 媒体查询
```css
/* 平板设备 */
@media screen and (max-width: 992px) {
    .layui-side {
        width: 200px;
    }
    
    .layui-body {
        left: 200px;
    }
    
    .project-card {
        width: calc(50% - 16px);
    }
}

/* 手机设备 */
@media screen and (max-width: 768px) {
    .layui-side {
        position: fixed;
        left: -220px;
        transition: left 0.3s;
        z-index: 999;
    }
    
    .layui-side.show {
        left: 0;
    }
    
    .layui-body {
        left: 0;
        padding: var(--spacing-sm);
    }
    
    .project-card {
        width: 100%;
    }
    
    /* 添加菜单切换按钮 */
    .menu-toggle {
        display: block;
        position: fixed;
        top: 10px;
        left: 10px;
        z-index: 1001;
    }
}
```

---

## 5. 后端设计

### 5.1 项目结构

```
AIJian/
├── 启动应用.bat               # ⭐ 一键启动脚本（推荐入口）
├── check_system.py           # 🔍 系统检查与依赖检测
├── init_test_data.py         # 📊 初始化测试数据
├── requirements.txt          # 📋 Python 依赖清单
├── README.md                 # 📖 项目说明
├── START_HERE.md             # 🚀 快速入口指南
├── frontend/                 # 🎨 前端 Web 与桌面界面
│   ├── app.py               # Flask 主应用入口（含 WebSocket）
│   ├── templates/           # HTML 模板（业务页面 + 公共布局）
│   └── static/              # 静态资源（CSS/JS/图片/字体等）
├── backend/                 # 🤖 后端服务与 AI 引擎
│   ├── api/                 # API 路由与接口
│   ├── engine/              # AI 引擎与音视频处理核心
│   ├── services/            # 业务服务层
│   ├── config/              # 后端配置
│   ├── database/            # 数据库访问
│   ├── prompts/             # 提示词模板
│   ├── utils/               # 工具函数与日志
│   ├── core/                # 核心状态与调度
│   └── assets/              # 资源与示例文件
├── config/                  # ⚙️ 全局配置
├── database/                # 💾 数据库文件
├── logs/                    # 📁 运行日志
├── resource/                # 📦 AI 模型与模板资源
├── uploads/                 # 📥 用户上传文件
├── output/                  # 📤 导出结果文件
├── tests/                   # ✅ 自动化测试
├── 开发文档/                # 📚 完整开发文档
└── yolov8n.pt               # 🎯 YOLOv8 模型权重
```

### 5.2 Flask 应用初始化

#### 5.2.1 应用入口 (app.py)
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIJian - 应用入口 main
"""

import os
import sys
import io
import logging
from pathlib import Path

# ============================================================
# UTF-8 编码设置（最高优先级）
# ============================================================
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONLEGACYWINDOWSSTDIO'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

import warnings
warnings.filterwarnings('ignore')

# 重配置标准输出
if hasattr(sys.stdout, 'buffer'):
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, 
            encoding='utf-8', 
            errors='replace', 
            line_buffering=True
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, 
            encoding='utf-8', 
            errors='replace', 
            line_buffering=True
        )
    except Exception:
        pass

# ============================================================
# Flask 应用初始化
# ============================================================
from flask import Flask, render_template, send_from_directory, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import webview
import threading
import time

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 创建 Flask 应用
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / 'templates'),
    static_folder=str(BASE_DIR / 'static'),
    static_url_path='/static'
)

# 配置
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['JSON_AS_ASCII'] = False  # 支持中文 JSON
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16GB 文件上传限制

# CORS 支持
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Socket.IO 支持
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25
)

# ============================================================
# 日志配置
# ============================================================
log_dir = BASE_DIR / 'log'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            log_dir / f'run-{time.strftime("%Y-%m-%d")}.log',
            encoding='utf-8'
        ),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# ============================================================
# 注册蓝图（API 路由）
# ============================================================
from api import register_blueprints
register_blueprints(app)

# ============================================================
# 页面路由
# ============================================================
@app.route('/')
def index():
    """首页"""
    return render_template('index.html', 
                         desk_multilingual={'首页': '首页'},
                         areaID='china')

@app.route('/make-audio')
def make_audio_page():
    """音频生成页面"""
    return render_template('project/make_audio.html')

@app.route('/commentary-cut-slim')
def commentary_cut_slim():
    """解说剪辑页面"""
    return render_template('project/commentary_slim/index.html')

@app.route('/mixed-cut-slim')
def mixed_cut_slim():
    """混剪页面"""
    return render_template('project/mixed_slim/index.html')

# ============================================================
# WebSocket 事件处理
# ============================================================
@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    logger.info('客户端已连接')

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    logger.info('客户端已断开')

@socketio.on('start_task')
def handle_start_task(data):
    """处理任务启动"""
    from services.task_service import TaskService
    task_service = TaskService(socketio)
    task_service.start_task(data)

@socketio.on('cancel_task')
def handle_cancel_task(data):
    """处理任务取消"""
    from services.task_service import TaskService
    task_service = TaskService(socketio)
    task_service.cancel_task(data['task_id'])

# ============================================================
# 错误处理
# ============================================================
@app.errorhandler(404)
def not_found(error):
    return jsonify({'code': 404, 'msg': '页面不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f'服务器错误: {error}')
    return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

# ============================================================
# 启动函数
# ============================================================
def start_flask():
    """启动 Flask 服务器"""
    logger.info('正在启动 Flask 服务器...')
    logger.info('服务器地址: http://127.0.0.1:5000')
    socketio.run(
        app,
        host='127.0.0.1',
        port=5000,
        debug=False,
        use_reloader=False
    )

def start_webview():
    """启动 PyWebView 窗口"""
    logger.info('等待 Flask 服务器启动...')
    time.sleep(3)
    
    logger.info('创建应用窗口...')
    window = webview.create_window(
        'AIJian - 智能视频剪辑工具 v2.0',
        'http://127.0.0.1:5000/',
        width=1400,
        height=900,
        resizable=True,
        fullscreen=False,
        min_size=(1024, 768)
    )
    
    logger.info('启动 GUI 窗口...')
    webview.start()
    
    logger.info('GUI 窗口已关闭')

# ============================================================
# 主程序入口
# ============================================================
if __name__ == '__main__':
    try:
        print('=' * 70)
        print('         AIJian - 智能视频剪辑工具 v2.0')
        print('=' * 70)
        print('[INFO] 正在初始化...')
        
        # 在后台线程启动 Flask
        flask_thread = threading.Thread(
            target=start_flask,
            daemon=True
        )
        flask_thread.start()
        
        # 在主线程启动 PyWebView
        start_webview()
        
    except KeyboardInterrupt:
        print('\n[INFO] 程序已停止')
    except Exception as e:
        logger.error(f'程序异常: {e}', exc_info=True)
        print(f'\n[ERROR] 程序异常: {e}')
        input('\n按回车键退出...')
```

### 5.3 API 路由设计

#### 5.3.1 API 蓝图注册 (api/__init__.py)
```python
from flask import Blueprint
from api.video import video_bp
from api.audio import audio_bp
from api.project import project_bp
from api.model import model_bp
from api.task import task_bp

def register_blueprints(app):
    """注册所有 API 蓝图"""
    app.register_blueprint(video_bp, url_prefix='/api/video')
    app.register_blueprint(audio_bp, url_prefix='/api/audio')
    app.register_blueprint(project_bp, url_prefix='/api/project')
    app.register_blueprint(model_bp, url_prefix='/api/model')
    app.register_blueprint(task_bp, url_prefix='/api/task')
```

#### 5.3.2 项目管理 API (api/project.py)
```python
from flask import Blueprint, request, jsonify
from services.project_service import ProjectService
import logging

project_bp = Blueprint('project', __name__)
project_service = ProjectService()
logger = logging.getLogger(__name__)

@project_bp.route('/list', methods=['GET'])
def get_projects():
    """获取项目列表"""
    try:
        project_type = request.args.get('type', None)
        projects = project_service.get_all_projects(project_type)
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': projects
        })
    except Exception as e:
        logger.error(f'获取项目列表失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'获取失败: {str(e)}'
        }), 500

@project_bp.route('/create', methods=['POST'])
def create_project():
    """创建新项目"""
    try:
        data = request.get_json()
        
        # 校验参数
        required_fields = ['name', 'type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'code': 400,
                    'msg': f'缺少必要参数: {field}'
                }), 400
        
        # 创建项目
        project = project_service.create_project(
            name=data['name'],
            project_type=data['type'],
            description=data.get('description', ''),
            template=data.get('template', None)
        )
        
        return jsonify({
            'code': 0,
            'msg': '创建成功',
            'data': project
        })
    except Exception as e:
        logger.error(f'创建项目失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'创建失败: {str(e)}'
        }), 500

@project_bp.route('/detail/<project_id>', methods=['GET'])
def get_project_detail(project_id):
    """获取项目详情"""
    try:
        project = project_service.get_project(project_id)
        if not project:
            return jsonify({
                'code': 404,
                'msg': '项目不存在'
            }), 404
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': project
        })
    except Exception as e:
        logger.error(f'获取项目详情失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'获取失败: {str(e)}'
        }), 500

@project_bp.route('/update/<project_id>', methods=['PUT'])
def update_project(project_id):
    """更新项目"""
    try:
        data = request.get_json()
        project = project_service.update_project(project_id, data)
        
        return jsonify({
            'code': 0,
            'msg': '更新成功',
            'data': project
        })
    except Exception as e:
        logger.error(f'更新项目失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'更新失败: {str(e)}'
        }), 500

@project_bp.route('/delete/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """删除项目"""
    try:
        project_service.delete_project(project_id)
        return jsonify({
            'code': 0,
            'msg': '删除成功'
        })
    except Exception as e:
        logger.error(f'删除项目失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'删除失败: {str(e)}'
        }), 500

@project_bp.route('/upload', methods=['POST'])
def upload_video():
    """上传视频文件"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'code': 400,
                'msg': '没有上传文件'
            }), 400
        
        file = request.files['file']
        project_id = request.form.get('project_id')
        
        if not project_id:
            return jsonify({
                'code': 400,
                'msg': '缺少项目ID'
            }), 400
        
        # 保存文件
        file_info = project_service.save_video(project_id, file)
        
        return jsonify({
            'code': 0,
            'msg': '上传成功',
            'data': file_info
        })
    except Exception as e:
        logger.error(f'上传文件失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'上传失败: {str(e)}'
        }), 500

@project_bp.route('/export/<project_id>', methods=['POST'])
def export_project(project_id):
    """导出项目"""
    try:
        data = request.get_json()
        
        # 启动导出任务
        task_id = project_service.export_project(
            project_id=project_id,
            format=data.get('format', 'mp4'),
            quality=data.get('quality', 'high'),
            output_path=data.get('output_path', None)
        )
        
        return jsonify({
            'code': 0,
            'msg': '导出任务已创建',
            'data': {'task_id': task_id}
        })
    except Exception as e:
        logger.error(f'导出项目失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'导出失败: {str(e)}'
        }), 500
```

#### 5.3.3 视频处理 API (api/video.py)
```python
from flask import Blueprint, request, jsonify
from services.video_service import VideoService
import logging

video_bp = Blueprint('video', __name__)
video_service = VideoService()
logger = logging.getLogger(__name__)

@project_bp.route('/analyze', methods=['POST'])
def analyze_video():
    """分析视频"""
    try:
        data = request.get_json()
        
        task_id = video_service.analyze_video(
            video_path=data['video_path'],
            options=data.get('options', {})
        )
        
        return jsonify({
            'code': 0,
            'msg': '分析任务已创建',
            'data': {'task_id': task_id}
        })
    except Exception as e:
        logger.error(f'视频分析失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'分析失败: {str(e)}'
        }), 500

@video_bp.route('/cut', methods=['POST'])
def cut_video():
    """剪辑视频"""
    try:
        data = request.get_json()
        
        task_id = video_service.cut_video(
            video_path=data['video_path'],
            cuts=data['cuts'],  # [{start: 10, end: 20}, ...]
            output_path=data.get('output_path', None)
        )
        
        return jsonify({
            'code': 0,
            'msg': '剪辑任务已创建',
            'data': {'task_id': task_id}
        })
    except Exception as e:
        logger.error(f'视频剪辑失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'剪辑失败: {str(e)}'
        }), 500

@video_bp.route('/merge', methods=['POST'])
def merge_videos():
    """合并视频"""
    try:
        data = request.get_json()
        
        task_id = video_service.merge_videos(
            video_paths=data['video_paths'],
            transitions=data.get('transitions', []),
            output_path=data.get('output_path', None)
        )
        
        return jsonify({
            'code': 0,
            'msg': '合并任务已创建',
            'data': {'task_id': task_id}
        })
    except Exception as e:
        logger.error(f'视频合并失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'合并失败: {str(e)}'
        }), 500

@video_bp.route('/add-audio', methods=['POST'])
def add_audio_to_video():
    """为视频添加音频"""
    try:
        data = request.get_json()
        
        task_id = video_service.add_audio(
            video_path=data['video_path'],
            audio_path=data['audio_path'],
            mix_mode=data.get('mix_mode', 'replace'),
            volume=data.get('volume', 1.0),
            output_path=data.get('output_path', None)
        )
        
        return jsonify({
            'code': 0,
            'msg': '任务已创建',
            'data': {'task_id': task_id}
        })
    except Exception as e:
        logger.error(f'添加音频失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'失败: {str(e)}'
        }), 500

@video_bp.route('/scene-detect', methods=['POST'])
def detect_scenes():
    """场景检测"""
    try:
        data = request.get_json()
        
        scenes = video_service.detect_scenes(
            video_path=data['video_path'],
            threshold=data.get('threshold', 0.3),
            min_scene_len=data.get('min_scene_len', 15)
        )
        
        return jsonify({
            'code': 0,
            'msg': '检测完成',
            'data': scenes
        })
    except Exception as e:
        logger.error(f'场景检测失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'检测失败: {str(e)}'
        }), 500
```

#### 5.3.4 音频处理 API (api/audio.py)
```python
from flask import Blueprint, request, jsonify
from services.audio_service import AudioService
import logging

audio_bp = Blueprint('audio', __name__)
audio_service = AudioService()
logger = logging.getLogger(__name__)

@audio_bp.route('/tts', methods=['POST'])
def text_to_speech():
    """文本转语音"""
    try:
        data = request.get_json()
        
        task_id = audio_service.generate_speech(
            text=data['text'],
            voice=data.get('voice', 'default'),
            speed=data.get('speed', 1.0),
            pitch=data.get('pitch', 0),
            volume=data.get('volume', 1.0),
            output_path=data.get('output_path', None)
        )
        
        return jsonify({
            'code': 0,
            'msg': 'TTS 任务已创建',
            'data': {'task_id': task_id}
        })
    except Exception as e:
        logger.error(f'TTS 失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'TTS 失败: {str(e)}'
        }), 500

@audio_bp.route('/asr', methods=['POST'])
def speech_to_text():
    """语音识别"""
    try:
        data = request.get_json()
        
        task_id = audio_service.recognize_speech(
            audio_path=data['audio_path'],
            language=data.get('language', 'zh'),
            model=data.get('model', 'whisper-large-v3')
        )
        
        return jsonify({
            'code': 0,
            'msg': 'ASR 任务已创建',
            'data': {'task_id': task_id}
        })
    except Exception as e:
        logger.error(f'ASR 失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'ASR 失败: {str(e)}'
        }), 500

@audio_bp.route('/mix', methods=['POST'])
def mix_audio():
    """混合音频"""
    try:
        data = request.get_json()
        
        task_id = audio_service.mix_audio(
            audio_paths=data['audio_paths'],
            volumes=data.get('volumes', [1.0] * len(data['audio_paths'])),
            output_path=data.get('output_path', None)
        )
        
        return jsonify({
            'code': 0,
            'msg': '混音任务已创建',
            'data': {'task_id': task_id}
        })
    except Exception as e:
        logger.error(f'混音失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'混音失败: {str(e)}'
        }), 500

@audio_bp.route('/denoise', methods=['POST'])
def denoise_audio():
    """音频降噪"""
    try:
        data = request.get_json()
        
        task_id = audio_service.denoise(
            audio_path=data['audio_path'],
            level=data.get('level', 'medium'),
            output_path=data.get('output_path', None)
        )
        
        return jsonify({
            'code': 0,
            'msg': '降噪任务已创建',
            'data': {'task_id': task_id}
        })
    except Exception as e:
        logger.error(f'降噪失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'降噪失败: {str(e)}'
        }), 500

@audio_bp.route('/voice-list', methods=['GET'])
def get_voice_list():
    """获取可用音色列表"""
    try:
        voices = audio_service.get_available_voices()
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': voices
        })
    except Exception as e:
        logger.error(f'获取音色列表失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'获取失败: {str(e)}'
        }), 500
```

#### 5.3.5 AI 模型 API (api/model.py)
```python
from flask import Blueprint, request, jsonify
from services.ai_service import AIService
import logging

model_bp = Blueprint('model', __name__)
ai_service = AIService()
logger = logging.getLogger(__name__)

@model_bp.route('/list', methods=['GET'])
def get_model_list():
    """获取模型列表"""
    try:
        model_type = request.args.get('type', None)
        models = ai_service.get_model_list(model_type)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': models
        })
    except Exception as e:
        logger.error(f'获取模型列表失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'获取失败: {str(e)}'
        }), 500

@model_bp.route('/download', methods=['POST'])
def download_model():
    """下载模型"""
    try:
        data = request.get_json()
        
        task_id = ai_service.download_model(
            model_id=data['model_id'],
            model_type=data.get('type', 'tts'),
            source=data.get('source', 'huggingface')
        )
        
        return jsonify({
            'code': 0,
            'msg': '下载任务已创建',
            'data': {'task_id': task_id}
        })
    except Exception as e:
        logger.error(f'下载模型失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'下载失败: {str(e)}'
        }), 500

@model_bp.route('/delete', methods=['DELETE'])
def delete_model():
    """删除模型"""
    try:
        model_id = request.args.get('model_id')
        ai_service.delete_model(model_id)
        
        return jsonify({
            'code': 0,
            'msg': '删除成功'
        })
    except Exception as e:
        logger.error(f'删除模型失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'删除失败: {str(e)}'
        }), 500

@model_bp.route('/info/<model_id>', methods=['GET'])
def get_model_info(model_id):
    """获取模型信息"""
    try:
        model_info = ai_service.get_model_info(model_id)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': model_info
        })
    except Exception as e:
        logger.error(f'获取模型信息失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'msg': f'获取失败: {str(e)}'
        }), 500
```

---

*由于文档篇幅限制，本文件为完整开发文档的第一部分。后续部分将重点介绍：*
- *业务逻辑层实现*
- *数据库设计与模型定义*
- *AI 模型集成与配置*
- *视频处理引擎封装*
- *部署打包与优化实践等内容*

**文档整体长度预计超过 2000 行，建议拆分为多个 Markdown 文件进行维护。**

---

## 继续阅读

请参考以下后续文档：
- `AIJian_完整开发文档_Part2.md` - 业务逻辑层与数据库设计
---
*由于文档篇幅限制，本文件为完整开发文档的第一部分。后续部分将重点介绍：*
- *业务逻辑层实现*
- *数据库设计与模型定义*
- *AI 模型集成与配置*
- *视频处理引擎封装*
- *部署打包与优化实践等内容*

**文档整体长度预计超过 2000 行，建议拆分为多个 Markdown 文件进行维护。**

---
## 继续阅读

请参考以下后续文档:
- `AIJian_完整开发文档_Part2.md` - 业务逻辑层与数据库设计
- `AIJian_完整开发文档_Part3.md` - AI 模型集成与视频处理引擎
- `AIJian_完整开发文档_Part4.md` - 部署打包与性能优化（如有）

---
**本文档持续更新中...**
