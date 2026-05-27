#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
提示词管理模块
包含原创解说提示词、黄金三秒开头、十大爆款钩子等
"""

from .narration_prompts import (
    NarrationPrompts,
    generate_narration_prompt
)

__all__ = [
    'NarrationPrompts',
    'generate_narration_prompt'
]
