#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
素材管理API路由
处理素材的上传、下载、列表等功能
"""

from flask import jsonify, request, send_file
from loguru import logger
import os
from pathlib import Path
from werkzeug.utils import secure_filename
import time


def register_material_routes(app, db_manager):
    """
    注册素材管理API路由
    
    Args:
        app: Flask应用实例
        db_manager: 数据库管理器实例
    """
    
    # 素材存储目录
    MATERIALS_DIR = Path('uploads/materials')
    MATERIALS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 允许的文件类型
    ALLOWED_EXTENSIONS = {
        'video': {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'},
        'audio': {'mp3', 'wav', 'aac', 'm4a', 'ogg', 'flac'},
        'image': {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'},
        'subtitle': {'srt', 'ass', 'vtt'}
    }
    
    def allowed_file(filename, file_type='video'):
        """检查文件类型是否允许"""
        if '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in ALLOWED_EXTENSIONS.get(file_type, set())
    
    
    @app.route('/api/upload/material', methods=['POST'])
    def upload_material():
        """上传素材文件"""
        try:
            # 检查是否有文件
            if 'file' not in request.files:
                return jsonify({
                    'code': 1,
                    'msg': '没有文件被上传',
                    'data': None
                }), 400
            
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({
                    'code': 1,
                    'msg': '文件名为空',
                    'data': None
                }), 400
            
            # 获取文件类型
            file_type = request.form.get('type', 'video')
            
            # 验证文件类型
            if not allowed_file(file.filename, file_type):
                return jsonify({
                    'code': 1,
                    'msg': f'不支持的文件类型',
                    'data': None
                }), 400
            
            # 安全的文件名
            filename = secure_filename(file.filename)
            timestamp = int(time.time() * 1000)
            safe_filename = f"{timestamp}_{filename}"
            
            # 保存文件
            file_path = MATERIALS_DIR / safe_filename
            file.save(str(file_path))
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            
            # 记录到数据库（如果需要）
            material_data = {
                'filename': filename,
                'safe_filename': safe_filename,
                'file_type': file_type,
                'file_size': file_size,
                'file_path': str(file_path),
                'upload_time': timestamp
            }
            
            logger.info(f'✅ 素材上传成功: {filename} ({file_size/1024/1024:.2f}MB)')
            
            return jsonify({
                'code': 0,
                'msg': '上传成功',
                'data': material_data
            })
            
        except Exception as e:
            logger.error(f'❌ 素材上传失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'上传失败: {str(e)}',
                'data': None
            }), 500
    
    
    @app.route('/api/material/download/<material_id>', methods=['GET'])
    def download_material(material_id):
        """下载素材文件"""
        try:
            # 从数据库获取素材信息（这里简化处理）
            # 实际应该从数据库查询
            materials_list = list(MATERIALS_DIR.glob('*'))
            
            # 查找文件
            material_file = None
            for file_path in materials_list:
                if material_id in file_path.name:
                    material_file = file_path
                    break
            
            if not material_file or not material_file.exists():
                return jsonify({
                    'code': 1,
                    'msg': '素材文件不存在',
                    'data': None
                }), 404
            
            logger.info(f'📥 下载素材: {material_file.name}')
            
            return send_file(
                str(material_file),
                as_attachment=True,
                download_name=material_file.name
            )
            
        except Exception as e:
            logger.error(f'❌ 素材下载失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'下载失败: {str(e)}',
                'data': None
            }), 500
    
    
    @app.route('/api/materials/list', methods=['GET'])
    def list_materials():
        """获取素材列表"""
        try:
            file_type = request.args.get('type', 'all')
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))

            # 需要遍历的物理目录：旧版素材库 + 通用上传目录
            base_uploads = Path('uploads')
            scan_dirs = [
                MATERIALS_DIR,
                base_uploads / 'videos',
                base_uploads / 'audios',
                base_uploads / 'images',
                base_uploads / 'commentary_videos',
                base_uploads / 'remix_videos'
            ]

            # 扩展名到类别的映射，便于根据 ?type=video/audio/image/subtitle 过滤
            ext_to_category = {}
            for cat, exts in ALLOWED_EXTENSIONS.items():
                for ext in exts:
                    ext_to_category[ext] = cat

            def match_type(ext: str) -> bool:
                """根据查询参数 file_type 判断是否保留该扩展名的文件"""
                if not ext:
                    return False
                if file_type == 'all':
                    return True
                cat = ext_to_category.get(ext)
                return cat == file_type

            # 收集所有素材文件
            materials_list = []
            seen = set()
            for d in scan_dirs:
                try:
                    if not d.exists():
                        continue
                    for file_path in d.glob('*'):
                        try:
                            if not file_path.is_file():
                                continue
                            real = file_path.resolve()
                            if real in seen:
                                continue
                            seen.add(real)

                            ext = file_path.suffix[1:].lower()
                            if not match_type(ext):
                                continue

                            stat = file_path.stat()
                            rel_path = str(file_path).replace('\\', '/')
                            file_info = {
                                'id': file_path.stem,
                                'filename': file_path.name,
                                'size': stat.st_size,
                                'modified_time': stat.st_mtime,
                                'type': ext,
                                'relative_path': rel_path
                            }
                            materials_list.append(file_info)
                        except Exception as ie:
                            logger.warning(f'⚠️ 扫描素材文件失败: {file_path}: {ie}')
                except Exception as de:
                    logger.warning(f'⚠️ 扫描素材目录失败: {d}: {de}')

            # 排序（按修改时间倒序）
            materials_list.sort(key=lambda x: x['modified_time'], reverse=True)

            # 分页
            total = len(materials_list)
            start = (page - 1) * per_page
            end = start + per_page
            materials_page = materials_list[start:end]

            logger.info(f'📋 获取素材列表: 第{page}页, 共{total}个')

            return jsonify({
                'code': 0,
                'msg': '获取成功',
                'data': {
                    'materials': materials_page,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total + per_page - 1) // per_page
                }
            })
            
        except Exception as e:
            logger.error(f'❌ 获取素材列表失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'获取失败: {str(e)}',
                'data': None
            }), 500
    
    
    @app.route('/api/material/delete/<material_id>', methods=['DELETE'])
    def delete_material(material_id):
        """删除素材文件"""
        try:
            # 查找文件
            materials_list = list(MATERIALS_DIR.glob('*'))
            material_file = None
            
            for file_path in materials_list:
                if material_id in file_path.name:
                    material_file = file_path
                    break
            
            if not material_file or not material_file.exists():
                return jsonify({
                    'code': 1,
                    'msg': '素材文件不存在',
                    'data': None
                }), 404
            
            # 删除文件
            material_file.unlink()
            
            logger.info(f'🗑️ 删除素材: {material_file.name}')
            
            return jsonify({
                'code': 0,
                'msg': '删除成功',
                'data': None
            })
            
        except Exception as e:
            logger.error(f'❌ 删除素材失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'删除失败: {str(e)}',
                'data': None
            }), 500
    
    
    logger.info('✅ 素材管理路由注册完成 (4个)')
