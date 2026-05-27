# -*- coding: utf-8 -*-
"""
Project API
项目管理API路由
"""

import logging
import os
import shutil
import time
from flask import request, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


def register_project_routes(app, db_manager):
    """
    注册项目管理相关的API路由
    
    Args:
        app: Flask应用实例
        db_manager: 数据库管理器实例
    """
    
    @app.route('/api/projects', methods=['GET'])
    def get_projects():
        """获取所有项目"""
        try:
            # 获取查询参数
            project_type = request.args.get('type')
            limit = request.args.get('limit', type=int)
            sort = request.args.get('sort', 'updated_at')
            order = request.args.get('order', 'desc')
            
            # 获取项目列表
            projects = db_manager.get_all_projects(project_type)
            
            # 如果没有项目，返回空列表
            if not projects:
                projects = []
            
            # 排序
            if sort and isinstance(projects, list):
                reverse = (order == 'desc')
                try:
                    projects.sort(key=lambda x: x.get(sort, ''), reverse=reverse)
                except:
                    pass
            
            # 限制数量
            if limit and isinstance(projects, list):
                projects = projects[:limit]
            
            # 返回符合前端期望的格式
            return jsonify({
                'code': 0, 
                'msg': '获取成功', 
                'data': {
                    'projects': projects,
                    'total': len(projects)
                }
            })
        except Exception as e:
            logger.error(f'获取项目列表失败: {e}', exc_info=True)
            return jsonify({
                'code': 1, 
                'msg': f'获取失败: {str(e)}', 
                'data': {'projects': [], 'total': 0}
            }), 500
    
    @app.route('/api/projects/<project_id>', methods=['GET'])
    def get_project(project_id):
        """获取项目详情"""
        try:
            project = db_manager.get_project(project_id)
            if project:
                return jsonify({'code': 0, 'msg': '获取成功', 'data': project})
            else:
                return jsonify({'code': 1, 'msg': '项目不存在', 'data': None}), 404
        except Exception as e:
            logger.error(f'获取项目详情失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'获取失败: {str(e)}', 'data': None}), 500
    
    @app.route('/api/projects', methods=['POST'])
    def create_project():
        """创建项目"""
        try:
            data = request.get_json()
            if not data or 'name' not in data or 'type' not in data:
                return jsonify({'code': 1, 'msg': '参数错误：缺少name或type', 'data': None}), 400
            
            project = db_manager.create_project(
                name=data.get('name'),
                project_type=data.get('type'),
                description=data.get('description', ''),
                template=data.get('template')
            )
            return jsonify({'code': 0, 'msg': '创建成功', 'data': project})
        except Exception as e:
            logger.error(f'创建项目失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'创建失败: {str(e)}', 'data': None}), 500
    
    @app.route('/api/projects/<project_id>', methods=['PUT'])
    def update_project(project_id):
        """更新项目"""
        try:
            data = request.get_json()
            project = db_manager.update_project(project_id, data)
            if project:
                return jsonify({'code': 0, 'msg': '更新成功', 'data': project})
            else:
                return jsonify({'code': 1, 'msg': '项目不存在', 'data': None}), 404
        except Exception as e:
            logger.error(f'更新项目失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'更新失败: {str(e)}', 'data': None}), 500
    
    @app.route('/api/projects/<project_id>', methods=['DELETE'])
    def delete_project(project_id):
        """删除项目"""
        try:
            db_manager.delete_project(project_id)
            return jsonify({'code': 0, 'msg': '删除成功', 'data': None})
        except Exception as e:
            logger.error(f'删除项目失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'删除失败: {str(e)}', 'data': None}), 500
    
    @app.route('/api/materials', methods=['GET'])
    def get_materials():
        """获取素材列表"""
        try:
            project_id = request.args.get('project_id')
            materials = db_manager.get_materials(project_id)
            return jsonify({'code': 0, 'msg': '获取成功', 'data': materials})
        except Exception as e:
            logger.error(f'获取素材列表失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'获取失败: {str(e)}', 'data': None}), 500
    
    @app.route('/api/materials', methods=['POST'])
    def create_material():
        """创建素材"""
        try:
            data = request.get_json()
            material = db_manager.create_material(
                project_id=data.get('project_id'),
                material_type=data.get('type'),
                name=data.get('name'),
                path=data.get('path'),
                size=data.get('size', 0),
                duration=data.get('duration', 0),
                metadata=data.get('metadata')
            )
            return jsonify({'code': 0, 'msg': '创建成功', 'data': material})
        except Exception as e:
            logger.error(f'创建素材失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'创建失败: {str(e)}', 'data': None}), 500
    
    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        """上传文件"""
        try:
            if 'file' not in request.files:
                return jsonify({'code': 1, 'msg': '没有文件', 'data': None}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'code': 1, 'msg': '文件名为空', 'data': None}), 400
            
            filename = secure_filename(file.filename)
            file_id = str(uuid.uuid4())
            file_ext = Path(filename).suffix
            save_filename = f"{file_id}{file_ext}"
            
            file_type = request.form.get('type', 'other')
            upload_dir = Path(app.config['UPLOAD_FOLDER']) / file_type
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            save_path = upload_dir / save_filename
            file.save(str(save_path))
            
            file_size = save_path.stat().st_size
            
            return jsonify({
                'code': 0,
                'msg': '上传成功',
                'data': {
                    'file_id': file_id,
                    'filename': filename,
                    'path': str(save_path),
                    'size': file_size,
                    'type': file_type
                }
            })
        except Exception as e:
            logger.error(f'文件上传失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'上传失败: {str(e)}', 'data': None}), 500
    
    @app.route('/api/project/stats', methods=['GET'])
    def get_project_stats():
        """获取项目统计信息"""
        try:
            # 获取所有项目
            projects = db_manager.get_all_projects()
            
            # 统计数据
            total = len(projects)
            processing = sum(1 for p in projects if p.get('status') == 'processing')
            completed = sum(1 for p in projects if p.get('status') == 'completed')
            failed = sum(1 for p in projects if p.get('status') == 'failed')
            
            stats = {
                'total': total,
                'processing': processing,
                'completed': completed,
                'failed': failed,
                'success_rate': f'{(completed / total * 100):.1f}%' if total > 0 else '0%'
            }
            
            logger.info(f'📊 项目统计: 总计{total}, 处理中{processing}, 已完成{completed}')
            
            return jsonify({
                'code': 0,
                'msg': '获取成功',
                'data': stats
            })
            
        except Exception as e:
            logger.error(f'❌ 获取项目统计失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'获取失败: {str(e)}',
                'data': None
            }), 500
    
    @app.route('/api/activity/timeline', methods=['GET'])
    def get_activity_timeline():
        """获取活动时间线"""
        try:
            limit = int(request.args.get('limit', 20))
            
            # 获取最近的项目活动
            projects = db_manager.get_all_projects()
            
            # 构建活动时间线
            activities = []
            for project in projects[:limit]:
                activity = {
                    'id': project.get('id'),
                    'type': 'project',
                    'action': project.get('status', 'created'),
                    'title': project.get('name', '未命名项目'),
                    'description': f"项目{project.get('status', '创建')}",
                    'timestamp': project.get('created_at', project.get('updated_at')),
                    'user': 'System'
                }
                activities.append(activity)
            
            # 按时间倒序排序
            activities.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            
            logger.info(f'📅 获取活动时间线: {len(activities)}条记录')
            
            return jsonify({
                'code': 0,
                'msg': '获取成功',
                'data': {'activities': activities[:limit]}
            })
            
        except Exception as e:
            logger.error(f'❌ 获取活动时间线失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'获取失败: {str(e)}',
                'data': None
            }), 500
    
    @app.route('/api/activity/<activity_id>', methods=['DELETE'])
    def delete_activity(activity_id):
        """删除活动记录"""
        try:
            # 这里删除活动实际上是删除对应的项目
            # 因为活动是基于项目生成的
            result = db_manager.delete_project(activity_id)
            
            if result:
                logger.info(f'🗑️ 删除活动记录成功: {activity_id}')
                return jsonify({
                    'code': 0,
                    'msg': '删除成功',
                    'data': {'id': activity_id}
                })
            else:
                return jsonify({
                    'code': 1,
                    'msg': '活动记录不存在',
                    'data': None
                }), 404
                
        except Exception as e:
            logger.error(f'❌ 删除活动记录失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'删除失败: {str(e)}',
                'data': None
            }), 500
    
    @app.route('/api/projects/batch-delete', methods=['POST'])
    def batch_delete_projects():
        """批量删除项目"""
        try:
            data = request.get_json()
            project_ids = data.get('project_ids', [])
            
            if not project_ids:
                return jsonify({
                    'code': 1,
                    'msg': '请选择要删除的项目',
                    'data': None
                }), 400
            
            # 删除所有指定的项目
            deleted_count = 0
            for project_id in project_ids:
                if db_manager.delete_project(project_id):
                    deleted_count += 1
            
            logger.info(f'🗑️ 批量删除项目成功: {deleted_count}/{len(project_ids)}')
            
            return jsonify({
                'code': 0,
                'msg': f'成功删除{deleted_count}个项目',
                'data': {
                    'deleted_count': deleted_count,
                    'total': len(project_ids)
                }
            })
            
        except Exception as e:
            logger.error(f'❌ 批量删除项目失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'批量删除失败: {str(e)}',
                'data': None
            }), 500
    
    @app.route('/api/system/metrics', methods=['GET'])
    def get_system_metrics():
        """获取系统实时指标（用于设置页动态展示）"""
        try:
            base_dir = Path(__file__).parent.parent.parent

            def dir_size(path: Path) -> int:
                total = 0
                try:
                    if path.exists():
                        for root, dirs, files in os.walk(str(path)):
                            for f in files:
                                fp = os.path.join(root, f)
                                try:
                                    total += os.path.getsize(fp)
                                except Exception:
                                    pass
                except Exception:
                    pass
                return total

            # 存储统计
            uploads_dir = base_dir / 'uploads'
            output_dir = base_dir / 'output'
            database_file = Path(getattr(db_manager, 'db_path', base_dir / 'database' / 'jjyb_ai.db'))

            app_used = dir_size(uploads_dir) + dir_size(output_dir)
            try:
                app_used += database_file.stat().st_size if database_file.exists() else 0
            except Exception:
                pass

            du = shutil.disk_usage(str(base_dir))
            storage = {
                'disk_total': du.total,
                'disk_used': du.total - du.free,
                'disk_free': du.free,
                'app_used': app_used,
                'uploads': dir_size(uploads_dir),
                'output': dir_size(output_dir),
                'database': (database_file.stat().st_size if database_file.exists() else 0)
            }

            # 项目统计
            projects = db_manager.get_all_projects()
            total = len(projects or [])
            processing = sum(1 for p in (projects or []) if str(p.get('status', '')).lower() in ('processing', 'running'))
            completed = sum(1 for p in (projects or []) if str(p.get('status', '')).lower() == 'completed')
            proj_stats = {
                'total': total,
                'processing': processing,
                'completed': completed
            }

            # API配置状态
            tts_default = ''
            voice_clone_enabled = False
            try:
                from backend.config.ai_config import get_config_manager
                cfg = get_config_manager()
                keys = [
                    # LLM
                    getattr(cfg.llm_config, 'custom_api_key', ''),
                    (getattr(cfg.llm_config, 'claude_api_key', '') or getattr(cfg.llm_config, 'anthropic_api_key', '')),
                    getattr(cfg.llm_config, 'gemini_api_key', ''),
                    (getattr(cfg.llm_config, 'qwen_api_key', '') or getattr(cfg.llm_config, 'tongyi_api_key', '')),
                    (getattr(cfg.llm_config, 'ernie_api_key', '') or getattr(cfg.llm_config, 'wenxin_api_key', '')),
                    getattr(cfg.llm_config, 'chatglm_api_key', ''),
                    getattr(cfg.llm_config, 'deepseek_api_key', ''),
                    getattr(cfg.llm_config, 'kimi_api_key', ''),
                    # Vision
                    (getattr(cfg.vision_config, 'qwen_vl_api_key', '') or getattr(cfg.vision_config, 'tongyi_vl_api_key', '')),
                    getattr(cfg.vision_config, 'baidu_vision_api_key', ''),
                    getattr(cfg.vision_config, 'gemini_vision_api_key', ''),
                    (getattr(cfg.vision_config, 'gpt4v_api_key', '') or getattr(cfg.vision_config, 'openai_vision_api_key', '')),
                    # TTS
                    (getattr(cfg.tts_model_config, 'azure_tts_key', '') or getattr(cfg.tts_model_config, 'azure_subscription_key', '')),
                ]
                api_configured = sum(1 for v in keys if v)
                # 默认TTS引擎与本地 Voice Clone 状态
                tts_default = getattr(cfg.tts_model_config, 'default_tts', '')
                voice_clone_enabled = getattr(cfg.tts_model_config, 'enable_voice_clone', False)
            except Exception:
                api_configured = 0

            # 引擎状态
            engines_count = 0
            try:
                from backend.core.global_state import get_global_state
                gs = get_global_state()
                eng = gs.get_system_status().get('engines_loaded', {})
                engines_count = sum(1 for v in eng.values() if v)
                system_state = gs.get_system_status()
            except Exception:
                system_state = {}

            # 运行时长（秒）
            try:
                app_start = getattr(db_manager, 'app_start_time', None)
                uptime_seconds = max(0, int(time.time() - app_start)) if app_start else 0
            except Exception:
                uptime_seconds = 0

            return jsonify({
                'code': 0,
                'msg': '获取成功',
                'data': {
                    'storage': storage,
                    'projects': proj_stats,
                    'api': {
                        'configured_count': api_configured
                    },
                    'system': {
                        'engines_loaded_count': engines_count,
                        'status': system_state,
                        'uptime_seconds': uptime_seconds,
                        'tts_default': tts_default,
                        'voice_clone_enabled': voice_clone_enabled
                    }
                }
            })
        except Exception as e:
            logger.error(f'❌ 获取系统指标失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500

    logger.info('✅ 项目管理API路由注册完成')
