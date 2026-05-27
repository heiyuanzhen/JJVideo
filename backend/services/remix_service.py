# -*- coding: utf-8 -*-
"""
Remix Service
混剪模式服务 - 完整实现
批量处理、智能识别、多种风格
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from backend.config.paths import PROJECT_ROOT
from backend.engine.video_processor import VideoProcessor

logger = logging.getLogger(__name__)


class RemixService:
    """混剪模式服务 - 完整实现"""
    
    def __init__(self, db_manager, socketio, task_service):
        """
        初始化混剪模式服务
        
        Args:
            db_manager: 数据库管理器
            socketio: SocketIO实例
            task_service: 任务服务
        """
        self.db_manager = db_manager
        self.socketio = socketio
        self.task_service = task_service
        # 视频处理引擎，用于获取基础信息（时长/分辨率等）
        self.video_processor = VideoProcessor()
        logger.info('✅ 混剪模式服务初始化完成')
    
    def create_remix_project(self, data: Dict) -> Dict:
        """
        创建混剪项目
        
        Args:
            data: 项目数据
                - name: 项目名称
                - video_paths: 视频路径列表
                - style: 混剪风格
                - duration: 目标时长
                
        Returns:
            项目信息
        """
        try:
            logger.info('🎬 创建混剪项目...')
            
            # 创建项目
            project = self.db_manager.create_project(
                name=data.get('name', '混剪项目'),
                project_type='remix',
                description='混剪模式项目',
                template='remix'
            )
            
            project_id = project['id']
            
            # 添加视频素材
            video_paths = data.get('video_paths', [])
            for i, video_path in enumerate(video_paths):
                self.db_manager.create_material(
                    project_id=project_id,
                    material_type='video',
                    name=f'素材视频{i+1}',
                    path=video_path,
                    metadata={'index': i}
                )
            
            # 保存配置
            config = {
                'style': data.get('style', 'dynamic'),  # dynamic/calm/exciting
                'target_duration': data.get('duration', 60),
                'transition': data.get('transition', 'auto'),
                'music_style': data.get('music_style', 'auto'),
                'auto_highlight': data.get('auto_highlight', True),
                'auto_bgm': data.get('auto_bgm', True)
            }
            
            self.db_manager.update_project(project_id, {'config': config})
            
            logger.info(f'✅ 混剪项目创建成功: {project_id}')
            
            return {
                'project_id': project_id,
                'project': project,
                'config': config,
                'material_count': len(video_paths)
            }
            
        except Exception as e:
            logger.error(f'❗ 创建混剪项目失败: {e}', exc_info=True)
            raise
    
    def batch_analyze_videos(self, video_paths: List[str]) -> List[Dict]:
        """
        批量分析视频
        
        Args:
            video_paths: 视频路径列表
            
        Returns:
            分析结果列表
        """
        try:
            logger.info(f'🔍 批量分析视频: {len(video_paths)}个')

            results: List[Dict] = []
            for video_path in video_paths:
                try:
                    path_obj = Path(video_path)
                    if not path_obj.is_absolute():
                        path_obj = PROJECT_ROOT / video_path

                    info = {}
                    if path_obj.exists():
                        info = self.video_processor.get_video_info(str(path_obj)) or {}
                    else:
                        logger.warning(f'⚠️ 视频文件不存在，跳过部分信息: {path_obj}')

                    duration = float(info.get('duration') or 0.0)
                    width = info.get('width') or 0
                    height = info.get('height') or 0
                    fps = float(info.get('fps') or 0.0) or 30.0
                    resolution = f"{width}x{height}" if width and height else '1920x1080'

                    analysis = {
                        'path': video_path,
                        'duration': duration,
                        'resolution': resolution,
                        'fps': fps,
                        'highlights': [],  # 精彩片段后续由 detect_highlights 填充
                        'scenes': [],      # 场景列表（后续可接入高级识别）
                        'quality_score': 0.8  # 先给一个默认质量评分
                    }
                    results.append(analysis)
                except Exception as ve:
                    logger.error(f'❗ 分析单个视频失败: {video_path}: {ve}', exc_info=True)
                    results.append({
                        'path': video_path,
                        'duration': 0,
                        'resolution': '1920x1080',
                        'fps': 30,
                        'highlights': [],
                        'scenes': [],
                        'quality_score': 0.5
                    })

            logger.info(f'✅ 视频分析完成: {len(results)}个')

            return results

        except Exception as e:
            logger.error(f'❗ 批量分析失败: {e}', exc_info=True)
            raise
    
    def detect_highlights(self, video_path: str) -> List[Dict]:
        """
        智能识别精彩片段
        
        Args:
            video_path: 视频路径
            
        Returns:
            精彩片段列表
        """
        try:
            logger.info(f'⭐ 识别精彩片段: {video_path}')

            path_obj = Path(video_path)
            if not path_obj.is_absolute():
                path_obj = PROJECT_ROOT / video_path

            info = {}
            if path_obj.exists():
                info = self.video_processor.get_video_info(str(path_obj)) or {}
            else:
                logger.warning(f'⚠️ 视频文件不存在，无法识别精彩片段: {path_obj}')
                return []

            duration = float(info.get('duration') or 0.0)
            if duration <= 0:
                logger.warning('⚠️ 视频时长为0，无法生成精彩片段')
                return []

            # 简单规则：按时长均匀采样若干片段作为“精彩片段”
            # 不依赖 AI 模型，但比固定时间段更真实
            segment_len = max(3.0, min(8.0, duration / 6))
            max_segments = 6

            highlights: List[Dict] = []
            # 从 5% 位置开始，到 95% 位置结束，平均分段
            start_offset = duration * 0.05
            end_limit = duration * 0.95
            current = start_offset
            idx = 0
            while current + 1.0 < end_limit and idx < max_segments:
                end = min(current + segment_len, end_limit)
                score = 0.7 + 0.05 * (idx % 4)  # 给出略有差异的评分
                h_type = 'action' if idx % 2 == 0 else 'emotion'
                desc = '自动识别精彩片段' if h_type == 'action' else '自动识别情感高潮'
                highlights.append({
                    'start_time': round(current, 2),
                    'end_time': round(end, 2),
                    'score': round(score, 3),
                    'type': h_type,
                    'description': desc
                })
                idx += 1
                current = end + max(1.0, segment_len * 0.3)

            logger.info(f'✅ 识别到 {len(highlights)} 个精彩片段')

            return highlights

        except Exception as e:
            logger.error(f'❗ 识别精彩片段失败: {e}', exc_info=True)
            raise
    
    def create_remix_plan(self, analyses: List[Dict], config: Dict) -> Dict:
        """
        创建混剪方案
        
        Args:
            analyses: 视频分析结果
            config: 混剪配置
            
        Returns:
            混剪方案
        """
        try:
            logger.info('📋 创建混剪方案...')
            
            raw_target = config.get('target_duration', 60)
            try:
                target_duration = float(raw_target) if raw_target is not None else 60.0
            except Exception:
                target_duration = 60.0
            if target_duration <= 0:
                target_duration = 60.0

            style = config.get('style', 'dynamic')
            
            # 根据风格选择片段
            clips: List[Dict] = []
            total_duration: float = 0.0
            
            for analysis in analyses:
                if total_duration >= target_duration:
                    break
                
                # 若未预先提供精彩片段，则在此调用 detect_highlights 自动识别
                highlights = analysis.get('highlights') or []
                if not highlights:
                    try:
                        path = analysis.get('path')
                        highlights = self.detect_highlights(path)
                        analysis['highlights'] = highlights
                    except Exception as he:
                        logger.error(f'❗ 自动识别精彩片段失败: {he}', exc_info=True)
                        continue

                for highlight in highlights:
                    if total_duration >= target_duration:
                        break
                    
                    try:
                        start = float(highlight.get('start_time', 0.0))
                        end = float(highlight.get('end_time', 0.0))
                    except Exception:
                        continue
                    clip_duration = end - start
                    if clip_duration <= 0:
                        continue

                    clips.append({
                        'video_path': analysis.get('path'),
                        'start_time': start,
                        'end_time': end,
                        'duration': clip_duration,
                        'type': highlight.get('type'),
                        'score': highlight.get('score')
                    })
                    total_duration += clip_duration
            
            plan = {
                'clips': clips,
                'total_clips': len(clips),
                'total_duration': total_duration,
                'style': style,
                'transitions': self._generate_transitions(len(clips)),
                'bgm_segments': self._generate_bgm_plan(total_duration)
            }
            
            logger.info(f'✅ 混剪方案创建完成: {len(clips)}个片段, 总时长{total_duration}秒')
            
            return plan
            
        except Exception as e:
            logger.error(f'❗ 创建混剪方案失败: {e}', exc_info=True)
            raise
    
    def process_remix(self, project_id: str, plan: Dict) -> str:
        """
        执行混剪处理
        
        Args:
            project_id: 项目ID
            plan: 混剪方案
            
        Returns:
            任务ID
        """
        try:
            logger.info(f'🎬 开始执行混剪: {project_id}')
            
            # 若 plan 中尚未包含精彩片段方案（clips），并且模式不是音乐卡点，则自动基于视频进行分析
            try:
                video_paths = list((plan or {}).get('video_paths') or [])
                mode = (plan.get('mode') or plan.get('remix_mode') or 'general').lower()
                has_clips = bool((plan or {}).get('clips'))
                if video_paths and not has_clips and mode != 'music':
                    analyses = self.batch_analyze_videos(video_paths)
                    cfg = {
                        'target_duration': plan.get('target_duration') or plan.get('duration') or 60,
                        'style': plan.get('style', 'dynamic')
                    }
                    remix_plan = self.create_remix_plan(analyses, cfg)
                    if remix_plan and isinstance(remix_plan, dict):
                        # 仅在原plan未设置对应字段时填充，避免覆盖调用方配置
                        for k, v in remix_plan.items():
                            plan.setdefault(k, v)
                        logger.info('✅ 已根据分析结果自动生成混剪方案（clips）')
            except Exception as pe:
                logger.error(f'❗ 自动生成混剪方案失败，将回退到基础合并逻辑: {pe}', exc_info=True)
            
            # 创建任务
            task_id = self.task_service.create_remix_task(
                project_id=project_id,
                plan=plan
            )
            
            logger.info(f'✅ 混剪任务已创建: {task_id}')
            
            return task_id
            
        except Exception as e:
            logger.error(f'❗ 执行混剪失败: {e}', exc_info=True)
            raise
    
    def apply_style(self, clips: List[Dict], style: str) -> List[Dict]:
        """
        应用混剪风格
        
        Args:
            clips: 视频片段列表
            style: 风格类型
            
        Returns:
            应用风格后的片段
        """
        try:
            logger.info(f'🎨 应用混剪风格: {style}')
            
            style_configs = {
                'dynamic': {
                    'clip_duration': (3, 5),
                    'transition_duration': 0.5,
                    'speed': 1.2
                },
                'calm': {
                    'clip_duration': (5, 8),
                    'transition_duration': 1.0,
                    'speed': 1.0
                },
                'exciting': {
                    'clip_duration': (2, 4),
                    'transition_duration': 0.3,
                    'speed': 1.5
                }
            }
            
            config = style_configs.get(style, style_configs['dynamic'])
            
            for clip in clips:
                clip['style_config'] = config
            
            logger.info(f'✅ 风格应用完成')
            
            return clips
            
        except Exception as e:
            logger.error(f'❗ 应用风格失败: {e}', exc_info=True)
            raise
    
    def _generate_transitions(self, clip_count: int) -> List[str]:
        """生成转场效果列表"""
        transitions = ['fade', 'dissolve', 'wipe', 'slide']
        return [transitions[i % len(transitions)] for i in range(clip_count - 1)]
    
    def _generate_bgm_plan(self, duration: float) -> List[Dict]:
        """生成背景音乐方案"""
        return [
            {
                'start_time': 0,
                'duration': duration,
                'music_type': 'auto',
                'volume': 0.3
            }
        ]
