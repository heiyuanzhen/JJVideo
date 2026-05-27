# -*- coding: utf-8 -*-
"""
视频导出API
提供视频导出、格式转换、质量调整等功能
"""

from flask import Blueprint, request, jsonify, send_file
import os
import subprocess
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

export_bp = Blueprint('export', __name__)


def build_segment_filter_graph(clips_hint, filters_hint=None, input_label="0:v", output_label="outv"):
    """基于时间线剪辑信息构造一个示例性的片段级 filter_complex 字符串。

    当前仅用于日志和调试，不直接参与导出命令，后续可以按需启用。
    """
    try:
        if not clips_hint:
            return None

        # 只考虑视频片段，按开始时间排序
        video_clips = [c for c in clips_hint if (c or {}).get("type") == "video"]
        if not video_clips:
            return None

        video_clips = sorted(
            video_clips,
            key=lambda c: float((c or {}).get("start_sec") or 0.0)
        )

        # 预计算一份基于全局 filters_hint 的 EQ 参数
        base_eq_args = []
        try:
            if isinstance(filters_hint, dict) and filters_hint:
                b_raw = float(filters_hint.get("brightness") or 0.0)
                c_raw = float(filters_hint.get("contrast") or 0.0)
                s_raw = float(filters_hint.get("saturation") or 0.0)

                brightness = max(-1.0, min(1.0, b_raw / 100.0))
                contrast = max(0.0, min(2.0, 1.0 + c_raw / 100.0))
                saturation = max(0.0, min(3.0, 1.0 + s_raw / 100.0))

                if abs(brightness) > 1e-3:
                    base_eq_args.append(f"brightness={brightness:.3f}")
                if abs(contrast - 1.0) > 1e-3:
                    base_eq_args.append(f"contrast={contrast:.3f}")
                if abs(saturation - 1.0) > 1e-3:
                    base_eq_args.append(f"saturation={saturation:.3f}")
        except Exception as e:
            logger.warning("预计算 EQ 参数失败: %s", e)

        segment_filters = []
        seg_labels = []

        for idx, clip in enumerate(video_clips):
            c = clip or {}
            start = float(c.get("start_sec") or 0.0)
            duration = float(c.get("duration_sec") or 0.0)
            end = start + max(duration, 0.001)

            label_out = f"seg{idx}"
            parts = [f"[{input_label}]trim=start={start}:end={end},setpts=PTS-STARTPTS"]

            # 片段级倒放
            if c.get("reverse"):
                parts.append("reverse")

            # 片段级色彩匹配: 在全局 EQ 基础上略微提升一点对比/饱和度
            eq_args = list(base_eq_args)
            if c.get("color_match"):
                eq_args.append("saturation=1.10")
                eq_args.append("contrast=1.05")
            if eq_args:
                parts.append("eq=" + ":".join(eq_args))

            # 片段级防抖：这里使用一个轻量级锐化作为占位，后续可替换为 deshake
            if c.get("stabilize"):
                parts.append("unsharp=5:5:0.8:5:5:0.0")

            chain = ",".join(parts)
            segment_filters.append(f"{chain}[{label_out}]")
            seg_labels.append(f"[{label_out}]")

        if not segment_filters:
            return None

        concat = "".join(seg_labels) + f"concat=n={len(seg_labels)}:v=1:a=0[{output_label}]"
        filter_complex = ";".join(segment_filters + [concat])
        logger.info("示例片段级 filter_complex: %s", filter_complex)
        return filter_complex
    except Exception as e:
        logger.warning("构建片段级 filter_graph 失败: %s", e)
        return None


def register_export_routes(app, db_manager):
    """
    注册导出相关路由
    
    Args:
        app: Flask应用实例
        db_manager: 数据库管理器实例
    """
    
    @app.route('/api/export/video', methods=['POST'])
    def export_video():
        """
        导出视频
        
        请求参数:
            project_id: 项目ID
            format: 导出格式 (mp4, avi, mov, mkv)
            quality: 视频质量 (low, medium, high, ultra)
            resolution: 分辨率 (1920x1080, 1280x720, 3840x2160)
            fps: 帧率 (24, 30, 60)
            codec: 编码器 (h264, h265, vp9)
        
        返回:
            code: 状态码
            msg: 消息
            data: 导出文件信息
        """
        try:
            data = request.json
            project_id = data.get('project_id')
            export_format = data.get('format', 'mp4')
            quality = data.get('quality', 'high')
            resolution = data.get('resolution', '1920x1080')
            fps = data.get('fps', 30)
            codec = data.get('codec', 'h264')

            # 时间线特效提示（由前端收集）
            effects_hints = data.get('effects_hints') or {}
            clips_hint = effects_hints.get('clips') or []
            filters_hint = effects_hints.get('filters') or {}
            
            logger.info(f'🎬 开始导出项目: {project_id}, 格式: {export_format}, 质量: {quality}')
            
            # 验证项目是否存在
            project = db_manager.get_project(project_id)
            if not project:
                return jsonify({
                    'code': -1,
                    'msg': '项目不存在'
                }), 404
            
            # 创建导出目录
            export_dir = os.path.join('exports', project_id)
            os.makedirs(export_dir, exist_ok=True)
            
            # 生成输出文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"{project['name']}_{timestamp}.{export_format}"
            output_path = os.path.join(export_dir, output_filename)
            
            # 质量参数映射
            quality_presets = {
                'low': {'bitrate': '1000k', 'crf': '28'},
                'medium': {'bitrate': '2500k', 'crf': '23'},
                'high': {'bitrate': '5000k', 'crf': '18'},
                'ultra': {'bitrate': '10000k', 'crf': '15'}
            }
            
            preset = quality_presets.get(quality, quality_presets['high'])
            
            # 编码器映射
            codec_map = {
                'h264': 'libx264',
                'h265': 'libx265',
                'vp9': 'libvpx-vp9'
            }
            
            video_codec = codec_map.get(codec, 'libx264')
            
            # 构建FFmpeg命令
            # 注意：这里假设有输入视频文件，实际应该从项目数据中获取
            input_file = data.get('input_file', 'temp_input.mp4')

            # 根据时间线特效提示构建滤镜链（目前支持 eq/hue/reverse）
            filter_parts = []

            # 颜色调节（来自 currentFilters）
            try:
                if isinstance(filters_hint, dict) and filters_hint:
                    b_raw = float(filters_hint.get('brightness') or 0.0)
                    c_raw = float(filters_hint.get('contrast') or 0.0)
                    s_raw = float(filters_hint.get('saturation') or 0.0)
                    h_raw = float(filters_hint.get('hue') or 0.0)

                    # 映射到 eq/hue 合理范围
                    brightness = max(-1.0, min(1.0, b_raw / 100.0))
                    contrast = max(0.0, min(2.0, 1.0 + c_raw / 100.0))
                    saturation = max(0.0, min(3.0, 1.0 + s_raw / 100.0))

                    eq_args = []
                    if abs(brightness) > 1e-3:
                        eq_args.append(f"brightness={brightness:.3f}")
                    if abs(contrast - 1.0) > 1e-3:
                        eq_args.append(f"contrast={contrast:.3f}")
                    if abs(saturation - 1.0) > 1e-3:
                        eq_args.append(f"saturation={saturation:.3f}")
                    if eq_args:
                        filter_parts.append('eq=' + ':'.join(eq_args))

                    # 色相调节：-100..100 -> -180..180 度
                    if abs(h_raw) > 1e-3:
                        hue_deg = max(-180.0, min(180.0, h_raw * 1.8))
                        # 使用角度制（FFmpeg 支持 deg）
                        filter_parts.append(f"hue=h={hue_deg:.1f}*PI/180")
            except Exception as e:
                logger.warning(f'构建颜色滤镜失败: {e}')

            # 倒放标记：如果任意视频片段标记了 reverse，则整体加一个 reverse 滤镜
            try:
                if clips_hint and any(bool(c.get('reverse')) for c in clips_hint):
                    filter_parts.append('reverse')
            except Exception as e:
                logger.warning(f'处理倒放标记失败: {e}')

            filter_chain = ','.join(filter_parts) if filter_parts else None

            # 构建一个仅用于调试日志的片段级 filter_complex 示例，暂不参与实际导出
            try:
                segment_filter_complex = build_segment_filter_graph(clips_hint, filters_hint)
                if segment_filter_complex:
                    logger.debug('调试: 可用于片段级导出的 filter_complex: %s', segment_filter_complex)
            except Exception as e:
                logger.warning('生成片段级 filter_complex 示例失败: %s', e)

            ffmpeg_cmd = ['ffmpeg', '-i', input_file]
            if filter_chain:
                ffmpeg_cmd += ['-vf', filter_chain]
            ffmpeg_cmd += [
                '-c:v', video_codec,
                '-b:v', preset['bitrate'],
                '-crf', preset['crf'],
                '-s', resolution,
                '-r', str(fps),
                '-c:a', 'aac',
                '-b:a', '192k',
                '-y',  # 覆盖输出文件
                output_path
            ]
            
            logger.info(f'📦 FFmpeg命令: {" ".join(ffmpeg_cmd)}')
            
            try:
                # 执行FFmpeg命令
                result = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5分钟超时
                )
                
                if result.returncode != 0:
                    logger.error(f'❌ FFmpeg执行失败: {result.stderr}')
                    return jsonify({
                        'code': -1,
                        'msg': f'视频导出失败: {result.stderr[:200]}'
                    }), 500
                
                # 获取文件大小
                file_size = os.path.getsize(output_path)
                file_size_mb = file_size / (1024 * 1024)
                
                logger.info(f'✅ 视频导出成功: {output_filename}, 大小: {file_size_mb:.2f}MB')
                
                return jsonify({
                    'code': 0,
                    'msg': '导出成功',
                    'data': {
                        'file_path': output_path,
                        'file_name': output_filename,
                        'file_size': file_size,
                        'file_size_mb': round(file_size_mb, 2),
                        'format': export_format,
                        'quality': quality,
                        'resolution': resolution,
                        'fps': fps,
                        'download_url': f'/api/export/download/{project_id}/{output_filename}',
                        'effects_hints': effects_hints,
                        'filter_chain': filter_chain
                    }
                })
                
            except subprocess.TimeoutExpired:
                logger.error('❌ FFmpeg执行超时')
                return jsonify({
                    'code': -1,
                    'msg': '导出超时，请尝试降低视频质量或分辨率'
                }), 500
            except FileNotFoundError:
                logger.error('❌ FFmpeg未安装')
                return jsonify({
                    'code': -1,
                    'msg': 'FFmpeg未安装，请先安装FFmpeg'
                }), 500
                
        except Exception as e:
            logger.error(f'❌ 导出视频失败: {e}')
            return jsonify({
                'code': -1,
                'msg': f'导出失败: {str(e)}'
            }), 500
    
    @app.route('/api/export/download/<project_id>/<filename>', methods=['GET'])
    def download_export(project_id, filename):
        """
        下载导出的视频
        
        Args:
            project_id: 项目ID
            filename: 文件名
        
        Returns:
            视频文件
        """
        try:
            file_path = os.path.join('exports', project_id, filename)
            
            if not os.path.exists(file_path):
                return jsonify({
                    'code': -1,
                    'msg': '文件不存在'
                }), 404
            
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            logger.error(f'❌ 下载文件失败: {e}')
            return jsonify({
                'code': -1,
                'msg': f'下载失败: {str(e)}'
            }), 500
    
    @app.route('/api/export/progress/<task_id>', methods=['GET'])
    def get_export_progress(task_id):
        """
        获取导出进度
        
        Args:
            task_id: 任务ID
        
        Returns:
            进度信息
        """
        try:
            task = db_manager.get_task(task_id)
            if not task:
                return jsonify({
                    'code': -1,
                    'msg': '任务不存在',
                    'data': None
                }), 404

            progress = task.get('progress') or 0
            status = task.get('status') or 'pending'
            message = task.get('error_message') or ''

            return jsonify({
                'code': 0,
                'msg': '成功',
                'data': {
                    'task_id': task_id,
                    'progress': float(progress),
                    'status': status,
                    'message': message or status
                }
            })
        except Exception as e:
            logger.error(f'❌ 获取进度失败: {e}', exc_info=True)
            return jsonify({
                'code': -1,
                'msg': f'获取进度失败: {str(e)}'
            }), 500
    
    logger.info('✅ 导出API路由注册成功 (3个端点)')
