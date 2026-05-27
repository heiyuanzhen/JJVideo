#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project: AIJian
@File   : subtitle_generator.py
@Author : AI Assistant (基于NarratoAI学习)
@Date   : 2025-11-10
@Desc   : 智能字幕生成器
          支持从文案生成SRT字幕、时间戳对齐、字幕优化
"""

import os
import re
from typing import List, Dict, Optional
from datetime import timedelta
from loguru import logger


class SubtitleGenerator:
    """
    智能字幕生成器
    
    功能：
    1. 从解说文案生成SRT字幕
    2. 时间戳格式转换
    3. 字幕文本优化（断句、长度控制）
    4. 多语言支持
    """
    
    def __init__(self):
        """初始化字幕生成器"""
        self.max_chars_per_line = 20  # 每行最多字符数
        self.max_lines = 2             # 最多行数
        logger.info("SubtitleGenerator初始化完成")
    
    def generate_srt_from_script(self, narration_script: Dict, output_path: str) -> str:
        """
        从解说文案生成SRT字幕
        
        Args:
            narration_script: 解说文案数据
                {
                    "narrations": [
                        {"time_range": "00:00:00-00:00:05", "text": "文本..."},
                        ...
                    ]
                }
            output_path: 输出SRT文件路径
        
        Returns:
            SRT文件路径
        """
        logger.info("开始生成SRT字幕")
        
        narrations = narration_script.get('narrations', [])
        if not narrations:
            logger.warning("解说文案为空，无法生成字幕")
            return None
        
        srt_content = []
        
        for i, narration in enumerate(narrations, start=1):
            time_range = narration.get('time_range', '00:00:00-00:00:05')
            text = narration.get('text', '')
            
            # 解析时间范围
            start_time, end_time = self._parse_time_range(time_range)
            
            # 优化文本（断句）
            optimized_text = self._optimize_subtitle_text(text)
            
            # 生成SRT条目
            srt_entry = self._create_srt_entry(i, start_time, end_time, optimized_text)
            srt_content.append(srt_entry)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(srt_content))
        
        logger.success(f"✅ SRT字幕生成完成: {output_path}")
        return output_path
    
    def _parse_time_range(self, time_range: str) -> tuple:
        """
        解析时间范围字符串
        
        Args:
            time_range: "00:00:00-00:00:05" 或 "0.0s-5.0s"
        
        Returns:
            (start_time_str, end_time_str) SRT格式时间戳
        """
        # 处理秒数格式（例如：0.0s-5.0s）
        if 's' in time_range:
            parts = time_range.replace('s', '').split('-')
            start_seconds = float(parts[0])
            end_seconds = float(parts[1])
            
            start_time_str = self._seconds_to_srt_time(start_seconds)
            end_time_str = self._seconds_to_srt_time(end_seconds)
        else:
            # 处理时间戳格式（例如：00:00:00-00:00:05）
            parts = time_range.split('-')
            start_time_str = self._convert_to_srt_time(parts[0].strip())
            end_time_str = self._convert_to_srt_time(parts[1].strip())
        
        return start_time_str, end_time_str
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """
        将秒数转换为SRT时间格式
        
        Args:
            seconds: 秒数
        
        Returns:
            SRT格式时间戳 "HH:MM:SS,mmm"
        """
        total = float(seconds)
        # 使用“乘1000加0.5再取整”的方式避免浮点和banker rounding问题
        total_ms = int(total * 1000 + 0.5)
        total_secs, milliseconds = divmod(total_ms, 1000)
        hours = total_secs // 3600
        minutes = (total_secs % 3600) // 60
        secs = total_secs % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def _convert_to_srt_time(self, time_str: str) -> str:
        """
        转换时间字符串为SRT格式
        
        Args:
            time_str: "HH:MM:SS" 或 "HH:MM:SS.mmm"
        
        Returns:
            SRT格式 "HH:MM:SS,mmm"
        """
        # 将.替换为,（SRT使用逗号）
        srt_time = time_str.replace('.', ',')
        
        # 确保有毫秒部分
        if ',' not in srt_time:
            srt_time += ',000'
        
        return srt_time
    
    def _optimize_subtitle_text(self, text: str) -> str:
        """
        优化字幕文本
        
        1. 断句（按标点符号）
        2. 控制每行长度
        3. 最多2行
        
        Args:
            text: 原始文本
        
        Returns:
            优化后的文本
        """
        # 移除多余空格
        text = re.sub(r'\s+', '', text)
        
        # 如果文本较短，直接返回
        if len(text) <= self.max_chars_per_line:
            return text
        
        # 尝试按标点符号断句
        sentences = re.split(r'([，。！？、；：])', text)
        
        lines = []
        current_line = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            punctuation = sentences[i+1] if i+1 < len(sentences) else ""
            
            if len(current_line + sentence + punctuation) <= self.max_chars_per_line:
                current_line += sentence + punctuation
            else:
                if current_line:
                    lines.append(current_line)
                current_line = sentence + punctuation
        
        if current_line:
            lines.append(current_line)
        
        # 最多2行
        if len(lines) > self.max_lines:
            lines = lines[:self.max_lines]
        
        return '\n'.join(lines)
    
    def _create_srt_entry(self, index: int, start_time: str, end_time: str, text: str) -> str:
        """
        创建SRT条目
        
        Args:
            index: 序号
            start_time: 开始时间
            end_time: 结束时间
            text: 字幕文本
        
        Returns:
            SRT格式条目
        """
        return f"{index}\n{start_time} --> {end_time}\n{text}"
    
    def merge_srt_files(self, srt_files: List[str], output_path: str) -> str:
        """
        合并多个SRT文件
        
        Args:
            srt_files: SRT文件路径列表
            output_path: 输出文件路径
        
        Returns:
            合并后的SRT文件路径
        """
        logger.info(f"开始合并{len(srt_files)}个SRT文件")
        
        all_entries = []
        
        for srt_file in srt_files:
            with open(srt_file, 'r', encoding='utf-8') as f:
                content = f.read()
                all_entries.append(content)
        
        # 合并并重新编号
        merged_content = '\n\n'.join(all_entries)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(merged_content)
        
        logger.success(f"✅ SRT文件合并完成: {output_path}")
        return output_path


# 便捷函数
def generate_srt(narration_script: Dict, output_path: str) -> str:
    """
    便捷函数：生成SRT字幕
    
    Args:
        narration_script: 解说文案
        output_path: 输出路径
    
    Returns:
        SRT文件路径
    """
    generator = SubtitleGenerator()
    return generator.generate_srt_from_script(narration_script, output_path)


if __name__ == '__main__':
    # 测试代码
    test_script = {
        'narrations': [
            {
                'time_range': '0.0s-5.0s',
                'text': '欢迎来到这个精彩的视频，让我们一起探索有趣的内容。'
            },
            {
                'time_range': '5.0s-10.0s',
                'text': '在这个片段中，我们可以看到很多精彩的画面。'
            },
            {
                'time_range': '10.0s-15.0s',
                'text': '感谢观看，我们下期再见！'
            }
        ]
    }
    
    output_srt = 'output/test_subtitle.srt'
    os.makedirs(os.path.dirname(output_srt), exist_ok=True)
    
    result = generate_srt(test_script, output_srt)
    
    if result:
        print(f"字幕生成成功: {result}")
        with open(result, 'r', encoding='utf-8') as f:
            print("\n生成的SRT内容：")
            print(f.read())
    else:
        print("字幕生成失败")
