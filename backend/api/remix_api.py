# -*- coding: utf-8 -*-
"""
Remix API
混剪模式API - 完整实现
"""

import logging
import json
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

remix_bp = Blueprint('remix', __name__)
remix_service = None
_db_manager = None


def register_remix_routes(app, db_manager, task_service, remix_svc):
    """注册混剪模式API路由"""
    global remix_service, _db_manager
    remix_service = remix_svc
    _db_manager = db_manager
    app.register_blueprint(remix_bp, url_prefix='/api/remix')
    logger.info('✅ 混剪模式API路由注册完成')


@remix_bp.route('/create', methods=['POST'])
def create_remix_project():
    """创建混剪项目"""
    try:
        data = request.get_json()
        result = remix_service.create_remix_project(data)
        return jsonify({'code': 0, 'msg': '项目创建成功', 'data': result})
    except Exception as e:
        logger.error(f'创建混剪项目失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'创建失败: {str(e)}', 'data': None}), 500


@remix_bp.route('/analyze', methods=['POST'])
def analyze_videos():
    """批量分析视频"""
    try:
        data = request.get_json()
        video_paths = data.get('video_paths', [])
        results = remix_service.batch_analyze_videos(video_paths)
        return jsonify({'code': 0, 'msg': '分析完成', 'data': results})
    except Exception as e:
        logger.error(f'分析视频失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'分析失败: {str(e)}', 'data': None}), 500


@remix_bp.route('/highlights', methods=['POST'])
def detect_highlights():
    """识别精彩片段"""
    try:
        data = request.get_json()
        video_path = data.get('video_path')
        highlights = remix_service.detect_highlights(video_path)
        return jsonify({'code': 0, 'msg': '识别完成', 'data': highlights})
    except Exception as e:
        logger.error(f'识别精彩片段失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'识别失败: {str(e)}', 'data': None}), 500


@remix_bp.route('/create-plan', methods=['POST'])
def create_plan():
    """创建混剪方案"""
    try:
        data = request.get_json()
        plan = remix_service.create_remix_plan(data['analyses'], data['config'])
        return jsonify({'code': 0, 'msg': '方案创建成功', 'data': plan})
    except Exception as e:
        logger.error(f'创建方案失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'创建失败: {str(e)}', 'data': None}), 500


@remix_bp.route('/process', methods=['POST'])
def process_remix():
    """执行混剪"""
    try:
        data = request.get_json()
        task_id = remix_service.process_remix(data['project_id'], data['plan'])
        return jsonify({'code': 0, 'msg': '任务已创建', 'data': {'task_id': task_id}})
    except Exception as e:
        logger.error(f'执行混剪失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'执行失败: {str(e)}', 'data': None}), 500


@remix_bp.route('/generate', methods=['POST'])
def generate_remix():
    """统一的混剪生成入口

    前端 remix.html 中的 startRemix() 会调用此接口并传入：
        - name: 项目名称
        - video_paths: 源视频路径列表（上传后后端返回的路径或文件名）
        - style: 混剪风格（dynamic/calm/exciting/...）
        - target_duration: 目标时长
        - auto_highlight / auto_transition / auto_bgm: 若干自动选项
        - bgm_file / music_path: 背景音乐路径（音乐卡点模式）
        - transition_style: 转场风格

    此接口会：
        1）创建混剪项目；
        2）构造混剪 plan（包含视频列表、模式、BGM 等配置）；
        3）调用 RemixService.process_remix 启动后台任务；
        4）返回 project_id 与 task_id，供前端轮询进度。
    """
    try:
        if remix_service is None:
            return jsonify({'code': 1, 'msg': '混剪服务未初始化', 'data': None}), 500

        data = request.get_json() or {}

        name = data.get('name') or '混剪项目'
        video_paths = data.get('video_paths') or []
        if not isinstance(video_paths, list) or not video_paths:
            return jsonify({'code': 1, 'msg': '缺少视频素材 video_paths', 'data': None}), 400

        style = data.get('style') or 'dynamic'
        target_duration = data.get('target_duration') or data.get('duration') or 60
        transition_style = data.get('transition_style') or data.get('transition') or 'auto'

        # 混剪模式（general / music），前端目前使用 selectedRemixMode
        remix_mode = (data.get('remix_mode')
                      or data.get('mode')
                      or data.get('selected_mode')
                      or 'general')

        # 1. 创建项目及素材
        project_result = remix_service.create_remix_project({
            'name': name,
            'video_paths': video_paths,
            'style': style,
            'duration': target_duration,
            'transition': transition_style,
            'music_style': data.get('music_style', 'auto'),
            'auto_highlight': data.get('auto_highlight', True),
            'auto_bgm': data.get('auto_bgm', True)
        })

        project_id = project_result.get('project_id') or project_result.get('project', {}).get('id')
        if not project_id:
            return jsonify({'code': 1, 'msg': '创建混剪项目失败：未获得项目ID', 'data': None}), 500

        # 2. 构造混剪 plan（先以 TaskService 基础实现为主）
        plan = {
            'video_paths': video_paths,
            'target_duration': target_duration,
            'style': style,
            'transition_style': transition_style,
            'mode': remix_mode,
            'remix_mode': remix_mode,
            'auto_bgm': data.get('auto_bgm', True),
            # BGM / 音乐卡点相关
            'bgm_file': data.get('bgm_file'),
            'music_path': data.get('music_path'),
            # 预留音乐卡点高级配置（若前端传入则一并保存，方便今后 BeatRemixEngine 使用）
            'beat_detection': data.get('beat_detection') or data.get('beatDetection'),
            'beat_sensitivity': data.get('beat_sensitivity') or data.get('beatSensitivity'),
            'fast_keyframe': data.get('fast_keyframe') or data.get('fastKeyframe'),
            'slow_keyframe': data.get('slow_keyframe') or data.get('slowKeyframe'),
            'speed_curve': data.get('speed_curve') or data.get('speedCurve'),
            'beat_transition': data.get('beat_transition') or data.get('beatTransition'),
            'rhythm_match': data.get('rhythm_match') or data.get('rhythmMatch'),
            'sync_precision': data.get('sync_precision') or data.get('syncPrecision'),
            # 为调试保留原始配置
            'raw_config': data
        }

        # 3. 启动混剪任务
        task_id = remix_service.process_remix(project_id, plan)

        return jsonify({
            'code': 0,
            'msg': '混剪任务已创建',
            'data': {
                'project_id': project_id,
                'task_id': task_id,
                'plan': {
                    'mode': remix_mode,
                    'style': style,
                    'target_duration': target_duration,
                    'video_count': len(video_paths)
                }
            }
        })
    except Exception as e:
        logger.error(f'混剪生成失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'混剪生成失败: {str(e)}', 'data': None}), 500


@remix_bp.route('/progress/<task_id>', methods=['GET'])
def remix_progress(task_id):
    """查询混剪任务进度与结果

    前端 monitorRemixProgress(taskId) 轮询此接口，期望字段：
        - progress: 0-100
        - status: pending/running/completed/failed
        - video_url / output_file / duration / video_count 等（任务完成时）
    """
    try:
        if _db_manager is None:
            return jsonify({'code': 1, 'msg': '数据库管理器未初始化', 'data': None}), 500

        task = _db_manager.get_task(task_id)
        if not task:
            return jsonify({'code': 1, 'msg': '任务不存在', 'data': None}), 404

        # 解析 JSON 字段
        for key in ('input_data', 'output_data'):
            val = task.get(key)
            if isinstance(val, str) and val:
                try:
                    task[key] = json.loads(val)
                except Exception:
                    task[key] = {}

        output_data = task.get('output_data') or {}
        if not isinstance(output_data, dict):
            output_data = {}

        resp_data = {
            'task_id': task.get('id'),
            'project_id': output_data.get('project_id') or task.get('project_id'),
            'status': task.get('status'),
            'progress': task.get('progress') or 0,
            'error': task.get('error_message')
        }

        # 将输出结果关键字段扁平化，方便前端 showRemixResult 使用
        resp_data.update({
            'video_url': output_data.get('video_url'),
            'output_file': output_data.get('output_file'),
            'duration': output_data.get('duration'),
            'video_count': output_data.get('video_count'),
            'mode': output_data.get('mode')
        })

        return jsonify({'code': 0, 'msg': '获取成功', 'data': resp_data})
    except Exception as e:
        logger.error(f'获取混剪任务进度失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'获取失败: {str(e)}', 'data': None}), 500
