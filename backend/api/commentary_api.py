# -*- coding: utf-8 -*-
"""
Commentary API
原创解说剪辑API - 完整实现
"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# 创建蓝图
commentary_bp = Blueprint('commentary', __name__)

# 全局变量（将在注册时设置）
commentary_service = None


def register_commentary_routes(app, db_manager, task_service, commentary_svc):
    """
    注册原创解说剪辑API路由
    
    Args:
        app: Flask应用实例
        db_manager: 数据库管理器
        task_service: 任务服务
        commentary_svc: 原创解说服务
    """
    global commentary_service
    commentary_service = commentary_svc
    
    app.register_blueprint(commentary_bp, url_prefix='/api/commentary')
    logger.info('✅ 原创解说API路由注册完成')


@commentary_bp.route('/create', methods=['POST'])
def create_commentary_project():
    """创建原创解说项目"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({
                'code': 1,
                'msg': '参数错误：缺少项目名称',
                'data': None
            }), 400
        
        result = commentary_service.create_commentary_project(data)
        
        return jsonify({
            'code': 0,
            'msg': '项目创建成功',
            'data': result
        })
        
    except Exception as e:
        logger.error(f'创建原创解说项目失败: {e}', exc_info=True)
        return jsonify({
            'code': 1,
            'msg': f'创建失败: {str(e)}',
            'data': None
        }), 500


@commentary_bp.route('/generate-script', methods=['POST'])
def generate_script():
    """生成解说文稿"""
    try:
        data = request.get_json()
        
        if not data or 'project_id' not in data:
            return jsonify({
                'code': 1,
                'msg': '参数错误：缺少项目ID',
                'data': None
            }), 400
        
        project_id = data['project_id']
        video_info = data.get('video_info', {})
        
        script = commentary_service.generate_script(project_id, video_info)
        
        return jsonify({
            'code': 0,
            'msg': '文稿生成成功',
            'data': script
        })
        
    except Exception as e:
        logger.error(f'生成文稿失败: {e}', exc_info=True)
        return jsonify({
            'code': 1,
            'msg': f'生成失败: {str(e)}',
            'data': None
        }), 500


@commentary_bp.route('/process', methods=['POST'])
def process_commentary():
    """处理原创解说剪辑"""
    try:
        data = request.get_json()
        
        if not data or 'project_id' not in data:
            return jsonify({
                'code': 1,
                'msg': '参数错误：缺少项目ID',
                'data': None
            }), 400
        
        project_id = data['project_id']
        config = data.get('config', {})
        
        task_id = commentary_service.process_commentary(project_id, config)
        
        return jsonify({
            'code': 0,
            'msg': '任务已创建',
            'data': {'task_id': task_id}
        })
        
    except Exception as e:
        logger.error(f'处理原创解说失败: {e}', exc_info=True)
        return jsonify({
            'code': 1,
            'msg': f'处理失败: {str(e)}',
            'data': None
        }), 500


@commentary_bp.route('/auto-clip', methods=['POST'])
def auto_clip():
    """自动剪辑视频"""
    try:
        data = request.get_json()
        
        if not data or 'video_path' not in data or 'script' not in data:
            return jsonify({
                'code': 1,
                'msg': '参数错误：缺少必需参数',
                'data': None
            }), 400
        
        clips = commentary_service.auto_clip_video(
            data['video_path'],
            data['script']
        )
        
        return jsonify({
            'code': 0,
            'msg': '自动剪辑完成',
            'data': {'clips': clips}
        })
        
    except Exception as e:
        logger.error(f'自动剪辑失败: {e}', exc_info=True)
        return jsonify({
            'code': 1,
            'msg': f'剪辑失败: {str(e)}',
            'data': None
        }), 500


@commentary_bp.route('/add-voiceover', methods=['POST'])
def add_voiceover():
    """添加配音"""
    try:
        data = request.get_json()
        
        if not data or 'clips' not in data:
            return jsonify({
                'code': 1,
                'msg': '参数错误：缺少片段信息',
                'data': None
            }), 400
        
        clips = commentary_service.add_voice_over(
            data['clips'],
            data.get('voice_config', {})
        )
        
        return jsonify({
            'code': 0,
            'msg': '配音添加成功',
            'data': {'clips': clips}
        })
        
    except Exception as e:
        logger.error(f'添加配音失败: {e}', exc_info=True)
        return jsonify({
            'code': 1,
            'msg': f'添加失败: {str(e)}',
            'data': None
        }), 500


@commentary_bp.route('/generate-subtitles', methods=['POST'])
def generate_subtitles():
    """生成字幕"""
    try:
        data = request.get_json()
        
        if not data or 'script' not in data:
            return jsonify({
                'code': 1,
                'msg': '参数错误：缺少文稿',
                'data': None
            }), 400
        
        srt_path = commentary_service.generate_subtitles(data['script'])
        
        return jsonify({
            'code': 0,
            'msg': '字幕生成成功',
            'data': {'srt_path': srt_path}
        })
        
    except Exception as e:
        logger.error(f'生成字幕失败: {e}', exc_info=True)
        return jsonify({
            'code': 1,
            'msg': f'生成失败: {str(e)}',
            'data': None
        }), 500
