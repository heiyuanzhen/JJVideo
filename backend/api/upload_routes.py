"""
文件上传API路由
"""

import logging
import os
import time
from flask import request, jsonify
from werkzeug.utils import secure_filename

logger = logging.getLogger('AIJian')

# 允许的文件扩展名
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'aac', 'm4a', 'flac'}
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'}

# 上传目录
UPLOAD_DIR = 'uploads'


def allowed_file(filename, allowed_extensions):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def register_upload_routes(app):
    """注册文件上传路由"""
    
    # 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_DIR, 'videos'), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_DIR, 'audios'), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_DIR, 'images'), exist_ok=True)
    # 为不同业务场景预留的子目录（解说/混剪等）
    os.makedirs(os.path.join(UPLOAD_DIR, 'commentary_videos'), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_DIR, 'remix_videos'), exist_ok=True)
    
    @app.route('/api/upload/video', methods=['POST'])
    def upload_video():
        """上传视频文件"""
        try:
            if 'video' not in request.files:
                return jsonify({'code': 1, 'msg': '没有文件', 'data': None}), 400
            
            file = request.files['video']
            
            if file.filename == '':
                return jsonify({'code': 1, 'msg': '文件名为空', 'data': None}), 400
            
            if not allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
                return jsonify({'code': 1, 'msg': '不支持的文件格式', 'data': None}), 400
            
            # 生成安全的文件名
            filename = secure_filename(file.filename)
            timestamp = int(time.time())
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}_{timestamp}{ext}"
            
            # 根据业务场景选择子目录
            scene = (request.form.get('scene') or '').strip().lower()
            if scene == 'commentary':
                subdir = 'commentary_videos'
            elif scene == 'remix':
                subdir = 'remix_videos'
            else:
                subdir = 'videos'

            # 确保子目录存在
            save_dir = os.path.join(UPLOAD_DIR, subdir)
            os.makedirs(save_dir, exist_ok=True)

            # 保存文件（始终返回相对路径 uploads/... 便于前端直接使用）
            filepath = os.path.join(UPLOAD_DIR, subdir, new_filename)
            file.save(filepath)
            
            # 获取文件大小
            file_size = os.path.getsize(filepath)
            
            logger.info(f'✅ 视频上传成功: {filepath}')
            
            return jsonify({
                'code': 0,
                'msg': '上传成功',
                'data': {
                    'path': filepath,
                    'filename': new_filename,
                    'size': file_size
                }
            })
            
        except Exception as e:
            logger.error(f'❌ 视频上传失败: {e}')
            return jsonify({'code': 1, 'msg': f'上传失败: {str(e)}', 'data': None}), 500
    
    @app.route('/api/upload/audio', methods=['POST'])
    def upload_audio():
        """上传音频文件"""
        try:
            if 'audio' not in request.files:
                return jsonify({'code': 1, 'msg': '没有文件', 'data': None}), 400
            
            file = request.files['audio']
            
            if file.filename == '':
                return jsonify({'code': 1, 'msg': '文件名为空', 'data': None}), 400
            
            if not allowed_file(file.filename, ALLOWED_AUDIO_EXTENSIONS):
                return jsonify({'code': 1, 'msg': '不支持的文件格式', 'data': None}), 400
            
            filename = secure_filename(file.filename)
            timestamp = int(time.time())
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}_{timestamp}{ext}"
            
            filepath = os.path.join(UPLOAD_DIR, 'audios', new_filename)
            file.save(filepath)
            
            file_size = os.path.getsize(filepath)
            
            logger.info(f'✅ 音频上传成功: {filepath}')
            
            return jsonify({
                'code': 0,
                'msg': '上传成功',
                'data': {
                    'path': filepath,
                    'filename': new_filename,
                    'size': file_size
                }
            })
            
        except Exception as e:
            logger.error(f'❌ 音频上传失败: {e}')
            return jsonify({'code': 1, 'msg': f'上传失败: {str(e)}', 'data': None}), 500
    
    @app.route('/api/upload/image', methods=['POST'])
    def upload_image():
        """上传图片文件"""
        try:
            if 'image' not in request.files:
                return jsonify({'code': 1, 'msg': '没有文件', 'data': None}), 400
            
            file = request.files['image']
            
            if file.filename == '':
                return jsonify({'code': 1, 'msg': '文件名为空', 'data': None}), 400
            
            if not allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
                return jsonify({'code': 1, 'msg': '不支持的文件格式', 'data': None}), 400
            
            filename = secure_filename(file.filename)
            timestamp = int(time.time())
            name, ext = os.path.splitext(filename)
            new_filename = f"{name}_{timestamp}{ext}"
            
            filepath = os.path.join(UPLOAD_DIR, 'images', new_filename)
            file.save(filepath)
            
            file_size = os.path.getsize(filepath)
            
            logger.info(f'✅ 图片上传成功: {filepath}')
            
            return jsonify({
                'code': 0,
                'msg': '上传成功',
                'data': {
                    'path': filepath,
                    'filename': new_filename,
                    'size': file_size
                }
            })
            
        except Exception as e:
            logger.error(f'❌ 图片上传失败: {e}')
            return jsonify({'code': 1, 'msg': f'上传失败: {str(e)}', 'data': None}), 500
    
    logger.info('✅ 文件上传路由注册完成')
