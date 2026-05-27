"""
原创解说API路由 - 完整AI流程
"""

import logging
from flask import Blueprint, request, jsonify
import os
import uuid
import json

logger = logging.getLogger('AIJian')


def register_commentary_routes_enhanced(app, db_manager, task_service, socketio):
    """注册原创解说API路由（增强版）"""
    
    # 初始化增强服务
    from backend.services.commentary_service_enhanced import CommentaryServiceEnhanced
    commentary_service = CommentaryServiceEnhanced(db_manager, socketio, task_service)
    
    logger.info('✅ 原创解说API路由（增强版）注册完成')
    
    @app.route('/api/commentary/create', methods=['POST'])
    def create_commentary_project():
        """创建原创解说项目"""
        try:
            data = request.get_json()
            result = commentary_service.create_project(data)
            return jsonify(result)
        except Exception as e:
            logger.error(f'❌ 创建项目失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/commentary/analyze', methods=['POST'])
    def analyze_video():
        """分析视频画面"""
        try:
            data = request.get_json()
            video_path = data.get('video_path')
            
            if not video_path:
                return jsonify({'code': 1, 'msg': '缺少视频文件路径', 'data': None}), 400
            # 支持相对路径：相对项目根目录（backend/..）
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            if os.path.isabs(video_path):
                video_path_abs = video_path
            else:
                video_path_abs = os.path.normpath(os.path.join(base_dir, video_path))
            if not os.path.exists(video_path_abs):
                return jsonify({'code': 1, 'msg': '视频文件不存在', 'data': None}), 400
            
            # 创建临时任务（写入数据库，保持与原逻辑兼容）
            task_id = str(uuid.uuid4())
            project_id = f'temp_{task_id[:8]}'  # 使用task_id前缀作为project_id，避免冲突
            db_manager.create_task(
                task_id=task_id,
                task_type='video_analysis',
                project_id=project_id,
                input_data={'description': '视频画面分析', 'video_path': video_path_abs}
            )
            task = {'id': task_id}
            
            # 执行分析
            results = commentary_service._analyze_video(video_path_abs, task['id'])
            
            if results:
                # 移除不可序列化字段（如关键帧中的图像ndarray）并做JSON安全化
                try:
                    if isinstance(results.get('keyframes'), list):
                        for kf in results['keyframes']:
                            if isinstance(kf, dict) and 'image' in kf:
                                kf['image'] = None
                except Exception:
                    pass
                try:
                    safe_data = json.loads(json.dumps(results, ensure_ascii=False, default=lambda o: None))
                except Exception:
                    # 兜底：直接不带关键帧图像字段
                    safe_data = {'scenes': results.get('scenes'), 'descriptions': results.get('descriptions'), 'summary': results.get('summary')}
                return jsonify({'code': 0, 'msg': '分析完成', 'data': safe_data})
            else:
                return jsonify({'code': 1, 'msg': '分析失败', 'data': None}), 500
            
        except Exception as e:
            logger.error(f'❌ 视频分析失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/commentary/generate-script', methods=['POST'])
    def generate_script():
        """生成解说文案"""
        try:
            data = request.get_json()
            vision_results = data.get('vision_results')
            config = data.get('config', {})
            # 将前端单独传入的 llm_model 合并进配置，便于后端根据该值切换当前使用的LLM
            try:
                llm_model = data.get('llm_model')
                if llm_model:
                    config['llm'] = llm_model
            except Exception:
                pass
            
            if not vision_results:
                return jsonify({'code': 1, 'msg': '缺少视频分析结果', 'data': None}), 400
            
            # 创建临时任务
            task_id = str(uuid.uuid4())
            db_manager.create_task(
                task_id=task_id,
                task_type='script_generation',
                project_id='temp',
                input_data={'description': '文案生成'}
            )
            task = {'id': task_id}
            
            # 生成文案
            script = commentary_service._generate_script(vision_results, config, task['id'])
            
            if script:
                return jsonify({'code': 0, 'msg': '生成完成', 'data': script})
            else:
                return jsonify({'code': 1, 'msg': '生成失败', 'data': None}), 500
            
        except Exception as e:
            logger.error(f'❌ 文案生成失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/commentary/generate-voiceover', methods=['POST'])
    def generate_voiceover():
        """生成配音"""
        try:
            data = request.get_json()
            script = data.get('script')
            config = data.get('config', {})
            
            if not script:
                return jsonify({'code': 1, 'msg': '缺少文案', 'data': None}), 400
            
            # 创建临时任务
            task_id = str(uuid.uuid4())
            db_manager.create_task(
                task_id=task_id,
                task_type='voiceover_generation',
                project_id='temp',
                input_data={'description': '配音生成'}
            )
            task = {'id': task_id}
            
            # 生成配音
            audio_path = commentary_service._generate_voiceover(script, config, task['id'])
            
            if audio_path:
                return jsonify({'code': 0, 'msg': '生成完成', 'data': {'audio_path': audio_path}})
            else:
                return jsonify({'code': 1, 'msg': '生成失败', 'data': None}), 500
            
        except Exception as e:
            logger.error(f'❌ 配音生成失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/commentary/sync', methods=['POST'])
    def sync_all():
        """执行三同步"""
        try:
            data = request.get_json()
            video_path = data.get('video_path')
            audio_path = data.get('audio_path')
            script = data.get('script')
            vision_results = data.get('vision_results')
            
            if not all([video_path, audio_path, script, vision_results]):
                return jsonify({'code': 1, 'msg': '缺少必要参数', 'data': None}), 400
            
            # 创建临时任务
            task_id = str(uuid.uuid4())
            db_manager.create_task(
                task_id=task_id,
                task_type='sync_processing',
                project_id='temp',
                input_data={'description': '三同步处理', 'video_path': video_path, 'audio_path': audio_path}
            )
            task = {'id': task_id}
            
            # 执行同步
            sync_results = commentary_service._sync_all(
                video_path, audio_path, script, vision_results, task['id']
            )
            
            if sync_results:
                return jsonify({'code': 0, 'msg': '同步完成', 'data': sync_results})
            else:
                return jsonify({'code': 1, 'msg': '同步失败', 'data': None}), 500
            
        except Exception as e:
            logger.error(f'❌ 三同步失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/commentary/process', methods=['POST'])
    def process_video():
        """完整处理流程"""
        try:
            data = request.get_json()
            project_id = data.get('project_id')
            video_path = data.get('video_path')
            config = data.get('config', {})
            
            if not project_id or not video_path:
                return jsonify({'code': 1, 'msg': '缺少必要参数', 'data': None}), 400
            
            if not os.path.exists(video_path):
                return jsonify({'code': 1, 'msg': '视频文件不存在', 'data': None}), 400
            
            # 异步处理
            result = commentary_service.process_video(project_id, video_path, config)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f'❌ 处理失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/commentary/result/<project_id>', methods=['GET'])
    def get_result(project_id):
        """获取处理结果"""
        try:
            result = commentary_service.get_project_result(project_id)
            return jsonify(result)
        except Exception as e:
            logger.error(f'❌ 获取结果失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    return commentary_service
