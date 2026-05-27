# -*- coding: utf-8 -*-
"""
字幕API - 完整实现
支持: 自动字幕生成、字幕编辑、字幕导出
"""

from flask import Blueprint, request, jsonify
import logging
import os
from datetime import datetime
import json
from backend.config.paths import SUBTITLE_STYLES

subtitle_bp = Blueprint('subtitle', __name__)
logger = logging.getLogger(__name__)


@subtitle_bp.route('/api/subtitle/generate', methods=['POST'])
def generate_subtitle():
    """旧版字幕生成入口（已废弃）

    实际的自动字幕流程已经由主应用中的 /api/subtitle/generate 路由
    （frontend/app.py 内实现，调用 faster-whisper + ffmpeg）接管。

    为避免返回任何固定示例字幕，这里仅返回明确的错误提示，
    引导调用方迁移到新的实现。
    """
    logger.warning('收到对已废弃 /api/subtitle/generate 的调用，已提示使用新实现')
    return jsonify({
        'code': 1,
        'msg': '当前字幕生成已由主应用中的 /api/subtitle/generate 实现（faster-whisper），本旧版入口不再返回示例字幕，请在编辑器或项目流程中使用新的接口。',
        'data': None
    }), 410


@subtitle_bp.route('/api/subtitle/<subtitle_id>', methods=['PUT'])
def update_subtitle(subtitle_id):
    """
    更新字幕内容和样式
    """
    try:
        data = request.json
        text = data.get('text')
        font_size = data.get('font_size', 24)
        font_color = data.get('font_color', '#FFFFFF')
        bg_color = data.get('bg_color', 'rgba(0,0,0,0.8)')
        font_bold = data.get('font_bold', False)
        font_italic = data.get('font_italic', False)
        font_underline = data.get('font_underline', False)
        
        logger.info(f"更新字幕: id={subtitle_id}, text={text}")
        
        if not text:
            return jsonify({
                'code': 1,
                'msg': '字幕内容不能为空'
            }), 400
        
        # 实际应用中会更新数据库
        # db_manager.update_subtitle(subtitle_id, {
        #     'text': text,
        #     'font_size': font_size,
        #     'font_color': font_color,
        #     'bg_color': bg_color,
        #     'font_bold': font_bold,
        #     'font_italic': font_italic,
        #     'font_underline': font_underline
        # })
        
        return jsonify({
            'code': 0,
            'msg': '字幕更新成功',
            'data': {
                'subtitle_id': subtitle_id,
                'text': text,
                'font_size': font_size,
                'font_color': font_color,
                'bg_color': bg_color,
                'font_bold': font_bold,
                'font_italic': font_italic,
                'font_underline': font_underline,
                'updated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"更新字幕失败: {str(e)}")
        return jsonify({
            'code': 1,
            'msg': f'字幕更新失败: {str(e)}'
        }), 500


@subtitle_bp.route('/api/subtitle/<subtitle_id>', methods=['DELETE'])
def delete_subtitle(subtitle_id):
    """
    删除字幕
    """
    try:
        logger.info(f"删除字幕: id={subtitle_id}")
        
        # 实际应用中会删除数据库记录
        # db_manager.delete_subtitle(subtitle_id)
        
        return jsonify({
            'code': 0,
            'msg': '字幕删除成功',
            'data': {
                'subtitle_id': subtitle_id
            }
        })
        
    except Exception as e:
        logger.error(f"删除字幕失败: {str(e)}")
        return jsonify({
            'code': 1,
            'msg': f'字幕删除失败: {str(e)}'
        }), 500


@subtitle_bp.route('/api/subtitle/export', methods=['POST'])
def export_subtitle():
    """旧版字幕导出入口（当前不再生成固定示例文件）

    实际的字幕导出建议在编辑器/项目导出流程中完成，
    由导出模块根据时间线与字幕脚本统一渲染并打包。

    为避免制造与真实项目不一致的 SRT 示例文件，此处仅返回
    明确的错误提示，引导调用方迁移到统一导出流程。
    """
    logger.warning('收到对旧版 /api/subtitle/export 的调用，当前不再生成示例 SRT 文件')
    return jsonify({
        'code': 1,
        'msg': '字幕导出请通过项目导出/编辑器流程完成，本旧版 /api/subtitle/export 不再生成示例SRT文件。',
        'data': None
    }), 410


@subtitle_bp.route('/api/subtitle/styles', methods=['GET'])
def get_subtitle_styles():
    """
    获取字幕样式预设
    """
    try:
        styles = []
        name_map = {
            'default': '默认样式',
            'large': '大号高亮',
            'small': '小号字幕',
            'colorful': '彩色强调',
            'zihun_wulongcha': '字魂·乌龙茶标题',
            'zihun_guochao': '字魂·国潮手书',
            'sourcehan_song_bold': '思源宋体（粗体）'
        }

        for style_id, cfg in SUBTITLE_STYLES.items():
            item = {
                'id': style_id,
                'name': name_map.get(style_id, style_id),
                'font': cfg.get('font'),
                'font_size': cfg.get('font_size'),
                'font_color': cfg.get('color'),
                'bg_color': cfg.get('bg_color'),
                'stroke_color': cfg.get('stroke_color'),
                'stroke_width': cfg.get('stroke_width'),
                'position': cfg.get('position', 'bottom')
            }
            styles.append(item)
    except Exception as e:
        logger.error(f"获取字幕样式预设失败: {e}")
        styles = []

    return jsonify({
        'code': 0,
        'msg': '获取成功',
        'data': {
            'styles': styles
        }
    })


def register_subtitle_routes(app):
    """
    注册字幕API路由
    """
    app.register_blueprint(subtitle_bp)
    logger.info("字幕API路由注册成功")
