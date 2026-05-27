# -*- coding: utf-8 -*-
"""
API Module
API路由模块
"""

from .project_api import register_project_routes
from .task_api import register_task_routes
from .video_api import register_video_routes
from .ai_api import register_ai_routes
from .commentary_api import register_commentary_routes
from .remix_api import register_remix_routes
from .voiceover_api import register_voiceover_routes
from .voice_clone_api import register_voice_clone_routes

__all__ = [
    'register_project_routes',
    'register_task_routes',
    'register_video_routes',
    'register_ai_routes',
    'register_commentary_routes',
    'register_remix_routes',
    'register_voiceover_routes',
    'register_voice_clone_routes'
]
