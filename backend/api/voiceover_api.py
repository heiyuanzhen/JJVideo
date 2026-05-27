# -*- coding: utf-8 -*-
"""
Voiceover API
AI配音API - 完整实现
"""

import logging
from pathlib import Path

from flask import Blueprint, request, jsonify

from backend.config.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)

voiceover_bp = Blueprint('voiceover', __name__)
voiceover_service = None


def register_voiceover_routes(app, db_manager, voiceover_svc):
    """注册AI配音API路由"""
    global voiceover_service
    voiceover_service = voiceover_svc
    app.register_blueprint(voiceover_bp, url_prefix='/api/voiceover')
    logger.info('✅ AI配音API路由注册完成')


@voiceover_bp.route('/voices', methods=['GET'])
def get_voices():
    """获取可用音色列表"""
    try:
        language = request.args.get('language')
        gender = request.args.get('gender')
        voices = voiceover_service.get_available_voices(language, gender)
        return jsonify({'code': 0, 'msg': '获取成功', 'data': voices})
    except Exception as e:
        logger.error(f'获取音色列表失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'获取失败: {str(e)}', 'data': None}), 500


@voiceover_bp.route('/create', methods=['POST'])
def create_voiceover_project():
    """创建AI配音项目"""
    try:
        data = request.get_json()
        result = voiceover_service.create_voiceover_project(data)
        return jsonify({'code': 0, 'msg': '项目创建成功', 'data': result})
    except Exception as e:
        logger.error(f'创建AI配音项目失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'创建失败: {str(e)}', 'data': None}), 500


@voiceover_bp.route('/generate', methods=['POST'])
def generate_voiceover():
    """生成AI配音"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'code': 1, 'msg': '参数错误：缺少文本', 'data': None}), 400
        
        output_path = voiceover_service.generate_voiceover(
            data['text'],
            data.get('voice_config', {})
        )

        p = Path(output_path).resolve()
        try:
            rel = p.relative_to(PROJECT_ROOT)
            rel_str = str(rel).replace('\\', '/')
        except Exception:
            # 回退到 output/audios/ 文件名 的形式
            rel_str = f"output/audios/{p.name}"

        audio_url = '/' + rel_str.lstrip('/')
        return jsonify({'code': 0, 'msg': '生成成功', 'data': {'audio_path': rel_str, 'audio_url': audio_url}})
    except Exception as e:
        logger.error(f'生成配音失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'生成失败: {str(e)}', 'data': None}), 500


@voiceover_bp.route('/batch-generate', methods=['POST'])
def batch_generate():
    """批量生成配音"""
    try:
        data = request.get_json()
        if not data or 'texts' not in data:
            return jsonify({'code': 1, 'msg': '参数错误：缺少文本列表', 'data': None}), 400
        
        output_paths = voiceover_service.batch_generate_voiceovers(
            data['texts'],
            data.get('voice_config', {})
        )

        rel_list = []
        url_list = []
        for p_str in output_paths:
            if not p_str:
                rel_list.append(None)
                url_list.append(None)
                continue
            p = Path(p_str).resolve()
            try:
                rel = p.relative_to(PROJECT_ROOT)
                rel_str = str(rel).replace('\\', '/')
            except Exception:
                rel_str = f"output/audios/{p.name}"
            audio_url = '/' + rel_str.lstrip('/')
            rel_list.append(rel_str)
            url_list.append(audio_url)

        return jsonify({'code': 0, 'msg': '批量生成完成', 'data': {'audio_paths': rel_list, 'audio_urls': url_list}})
    except Exception as e:
        logger.error(f'批量生成失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'生成失败: {str(e)}', 'data': None}), 500


@voiceover_bp.route('/preview', methods=['POST'])
def preview_voice():
    """预览音色"""
    try:
        data = request.get_json()
        if not data or 'voice_id' not in data:
            return jsonify({'code': 1, 'msg': '参数错误：缺少音色ID', 'data': None}), 400
        engine = (data.get('engine') or '').strip() if data else ''

        audio_path = voiceover_service.preview_voice(
            data['voice_id'],
            data.get('sample_text'),
            engine=engine or None
        )

        p = Path(audio_path).resolve()
        try:
            rel = p.relative_to(PROJECT_ROOT)
            rel_str = str(rel).replace('\\', '/')
        except Exception:
            rel_str = f"output/previews/{p.name}"
        audio_url = '/' + rel_str.lstrip('/')

        return jsonify({'code': 0, 'msg': '预览生成成功', 'data': {'audio_path': rel_str, 'audio_url': audio_url}})
    except Exception as e:
        logger.error(f'预览音色失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'预览失败: {str(e)}', 'data': None}), 500


@voiceover_bp.route('/merge', methods=['POST'])
def merge_voiceovers():
    """合并配音"""
    try:
        data = request.get_json()
        if not data or 'audio_paths' not in data:
            return jsonify({'code': 1, 'msg': '参数错误：缺少音频路径列表', 'data': None}), 400
        
        output_path = voiceover_service.merge_voiceovers(
            data['audio_paths'],
            data.get('output_path')
        )

        p = Path(output_path).resolve()
        try:
            rel = p.relative_to(PROJECT_ROOT)
            rel_str = str(rel).replace('\\', '/')
        except Exception:
            rel_str = f"output/audios/{p.name}"
        audio_url = '/' + rel_str.lstrip('/')

        return jsonify({'code': 0, 'msg': '合并成功', 'data': {'audio_path': rel_str, 'audio_url': audio_url}})
    except Exception as e:
        logger.error(f'合并配音失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'合并失败: {str(e)}', 'data': None}), 500
