"""
配置管理API路由
处理所有配置的保存、读取和同步
"""

import logging
from dataclasses import asdict
from flask import request, jsonify

logger = logging.getLogger('AIJian')


def register_config_routes(app):
    """注册配置管理路由"""
    
    from backend.config.ai_config import get_config_manager
    from backend.core.global_state import get_global_state
    
    config_manager = get_config_manager()
    global_state = get_global_state()
    
    @app.route('/api/config/llm', methods=['GET'])
    def get_llm_config():
        """获取LLM配置"""
        try:
            config = {
                'tongyi_api_key': config_manager.llm_config.tongyi_api_key,
                'wenxin_api_key': config_manager.llm_config.wenxin_api_key,
                'chatglm_api_key': config_manager.llm_config.chatglm_api_key,
                'deepseek_api_key': config_manager.llm_config.deepseek_api_key,
                'custom_api_key': config_manager.llm_config.custom_api_key,
                'claude_api_key': config_manager.llm_config.claude_api_key,
                'gemini_api_key': config_manager.llm_config.gemini_api_key,
                'default_model': config_manager.llm_config.default_model
            }
            return jsonify({'code': 0, 'msg': '获取成功', 'data': config})
        except Exception as e:
            logger.error(f'❌ 获取LLM配置失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/config/llm', methods=['POST'])
    def save_llm_config():
        """保存LLM配置"""
        try:
            data = request.get_json()
            
            # 更新配置
            if 'tongyi_api_key' in data:
                config_manager.llm_config.tongyi_api_key = data['tongyi_api_key']
            if 'wenxin_api_key' in data:
                config_manager.llm_config.wenxin_api_key = data['wenxin_api_key']
            if 'chatglm_api_key' in data:
                config_manager.llm_config.chatglm_api_key = data['chatglm_api_key']
            if 'deepseek_api_key' in data:
                config_manager.llm_config.deepseek_api_key = data['deepseek_api_key']
            if 'custom_api_key' in data:
                config_manager.llm_config.custom_api_key = data['custom_api_key']
            if 'claude_api_key' in data:
                config_manager.llm_config.claude_api_key = data['claude_api_key']
            if 'gemini_api_key' in data:
                config_manager.llm_config.gemini_api_key = data['gemini_api_key']
            if 'default_model' in data:
                config_manager.llm_config.default_model = data['default_model']
                global_state.set_active_llm_model(data['default_model'])
            
            # 保存配置
            config_manager.save_config()
            
            # 重新加载全局状态
            global_state.reload_config()
            
            logger.info('✅ LLM配置保存成功')
            return jsonify({'code': 0, 'msg': '保存成功', 'data': None})
            
        except Exception as e:
            logger.error(f'❌ 保存LLM配置失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/config/vision', methods=['GET'])
    def get_vision_config():
        """获取视觉模型配置"""
        try:
            config = {
                'tongyi_vl_api_key': config_manager.vision_config.tongyi_vl_api_key,
                'baidu_vision_api_key': config_manager.vision_config.baidu_vision_api_key,
                'gemini_vision_api_key': config_manager.vision_config.gemini_vision_api_key,
                'openai_vision_api_key': config_manager.vision_config.openai_vision_api_key,
                'default_model': config_manager.vision_config.default_model
            }
            return jsonify({'code': 0, 'msg': '获取成功', 'data': config})
        except Exception as e:
            logger.error(f'❌ 获取视觉配置失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/config/vision', methods=['POST'])
    def save_vision_config():
        """保存视觉模型配置"""
        try:
            data = request.get_json()
            
            # 更新配置
            if 'tongyi_vl_api_key' in data:
                config_manager.vision_config.tongyi_vl_api_key = data['tongyi_vl_api_key']
            if 'baidu_vision_api_key' in data:
                config_manager.vision_config.baidu_vision_api_key = data['baidu_vision_api_key']
            if 'gemini_vision_api_key' in data:
                config_manager.vision_config.gemini_vision_api_key = data['gemini_vision_api_key']
            if 'openai_vision_api_key' in data:
                config_manager.vision_config.openai_vision_api_key = data['openai_vision_api_key']
            if 'default_model' in data:
                config_manager.vision_config.default_model = data['default_model']
                global_state.set_active_vision_model(data['default_model'])
            
            # 保存配置
            config_manager.save_config()
            global_state.reload_config()
            
            logger.info('✅ 视觉配置保存成功')
            return jsonify({'code': 0, 'msg': '保存成功', 'data': None})
            
        except Exception as e:
            logger.error(f'❌ 保存视觉配置失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/config/censor', methods=['GET'])
    def get_censor_config():
        """获取违禁词配置"""
        try:
            config = {
                'enable_censor': config_manager.censor_config.enable_censor,
                'censor_tool': config_manager.censor_config.censor_tool,
                'custom_words': config_manager.censor_config.custom_words
            }
            return jsonify({'code': 0, 'msg': '获取成功', 'data': config})
        except Exception as e:
            logger.error(f'❌ 获取违禁词配置失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/config/censor', methods=['POST'])
    def save_censor_config():
        """保存违禁词配置"""
        try:
            data = request.get_json()
            
            if 'enable_censor' in data:
                config_manager.censor_config.enable_censor = data['enable_censor']
            if 'censor_tool' in data:
                config_manager.censor_config.censor_tool = data['censor_tool']
            if 'custom_words' in data:
                config_manager.censor_config.custom_words = data['custom_words']
            
            config_manager.save_config()
            config_manager.save_censor_words()
            
            logger.info('✅ 违禁词配置保存成功')
            return jsonify({'code': 0, 'msg': '保存成功', 'data': None})
            
        except Exception as e:
            logger.error(f'❌ 保存违禁词配置失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/config/censor/add', methods=['POST'])
    def add_censor_word():
        """添加违禁词"""
        try:
            data = request.get_json()
            word = data.get('word')
            category = data.get('category', '其他')
            
            if not word:
                return jsonify({'code': 1, 'msg': '违禁词不能为空', 'data': None}), 400
            
            success = config_manager.add_censor_word(word, category)
            
            if success:
                return jsonify({'code': 0, 'msg': '添加成功', 'data': None})
            else:
                return jsonify({'code': 1, 'msg': '违禁词已存在', 'data': None}), 400
            
        except Exception as e:
            logger.error(f'❌ 添加违禁词失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/config/censor/remove', methods=['POST'])
    def remove_censor_word():
        """删除违禁词"""
        try:
            data = request.get_json()
            word = data.get('word')
            
            if not word:
                return jsonify({'code': 1, 'msg': '违禁词不能为空', 'data': None}), 400
            
            success = config_manager.remove_censor_word(word)
            
            if success:
                return jsonify({'code': 0, 'msg': '删除成功', 'data': None})
            else:
                return jsonify({'code': 1, 'msg': '违禁词不存在', 'data': None}), 400
            
        except Exception as e:
            logger.error(f'❌ 删除违禁词失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/config/models/available', methods=['GET'])
    def get_available_models():
        """获取所有可用的模型"""
        try:
            models = global_state.get_available_models()
            return jsonify({'code': 0, 'msg': '获取成功', 'data': models})
        except Exception as e:
            logger.error(f'❌ 获取可用模型失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/config/models/switch', methods=['POST'])
    def switch_model():
        """切换模型"""
        try:
            data = request.get_json()
            model_type = data.get('type')  # 'llm' or 'vision'
            model_name = data.get('model')
            
            if model_type == 'llm':
                global_state.set_active_llm_model(model_name)
            elif model_type == 'vision':
                global_state.set_active_vision_model(model_name)
            else:
                return jsonify({'code': 1, 'msg': '无效的模型类型', 'data': None}), 400
            
            return jsonify({'code': 0, 'msg': '切换成功', 'data': None})
            
        except Exception as e:
            logger.error(f'❌ 切换模型失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/config/system/status', methods=['GET'])
    def get_system_status():
        """获取系统状态"""
        try:
            status = global_state.get_system_status()
            return jsonify({'code': 0, 'msg': '获取成功', 'data': status})
        except Exception as e:
            logger.error(f'❌ 获取系统状态失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/config/reload', methods=['POST'])
    def reload_config():
        """重新加载配置"""
        try:
            success = global_state.reload_config()
            if success:
                return jsonify({'code': 0, 'msg': '重新加载成功', 'data': None})
            else:
                return jsonify({'code': 1, 'msg': '重新加载失败', 'data': None}), 500
        except Exception as e:
            logger.error(f'❌ 重新加载配置失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/config/get', methods=['GET'])
    def get_all_config():
        """获取所有配置（统一接口）"""
        try:
            config_data = {
                'llm': asdict(config_manager.llm_config),
                'vision': asdict(config_manager.vision_config),
                'tts_model': asdict(config_manager.tts_model_config),
                'proxy': asdict(config_manager.proxy_config),
                'tts': asdict(config_manager.tts_config),
                'censor': asdict(config_manager.censor_config),
                'global': asdict(config_manager.global_config),
                'local_model': asdict(config_manager.local_model_config)
            }
            return jsonify({'code': 0, 'msg': '获取配置成功', 'data': {'config': config_data}})
        except Exception as e:
            logger.error(f'❌ 获取配置失败: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    @app.route('/api/config/save', methods=['POST'])
    def save_all_config():
        """保存所有配置（统一接口）"""
        try:
            logger.info('=' * 80)
            logger.info('💾 [统一配置保存] 开始处理请求')

            data = request.get_json() or {}
            logger.info(f'📥 [统一配置保存] 接收到的数据键: {list(data.keys()) if data else "空"}')

            # 过滤空值与脱敏占位值，避免覆盖真实密钥
            def _should_keep(k, v):
                if v is None:
                    return False
                if isinstance(v, str):
                    s = v.strip()
                    if s == '':
                        return False
                    if ('api_key' in k.lower()) or ('secret' in k.lower()):
                        star = s.count('*')
                        if star >= 4 and star >= (len(s) // 2):
                            logger.info(f'🙈 [统一配置保存] 跳过脱敏/占位值: {k}')
                            return False
                return True
            data = {kk: vv for kk, vv in data.items() if _should_keep(kk, vv)}

            updated_keys = []

            # 保存LLM配置
            if 'custom_api_key' in data:
                config_manager.llm_config.custom_api_key = data['custom_api_key']
                updated_keys.append('custom_api_key')
            if 'custom_base_url' in data:
                config_manager.llm_config.custom_base_url = data['custom_base_url']
                updated_keys.append('custom_base_url')
            if 'custom_model' in data:
                config_manager.llm_config.custom_model = data['custom_model']
                updated_keys.append('custom_model')

            if 'anthropic_api_key' in data:
                config_manager.llm_config.anthropic_api_key = data['anthropic_api_key']
                updated_keys.append('anthropic_api_key')
            if 'anthropic_model' in data:
                config_manager.llm_config.anthropic_model = data['anthropic_model']
                updated_keys.append('anthropic_model')

            if 'gemini_api_key' in data:
                config_manager.llm_config.gemini_api_key = data['gemini_api_key']
                updated_keys.append('gemini_api_key')

            if 'kimi_api_key' in data:
                config_manager.llm_config.kimi_api_key = data['kimi_api_key']
                updated_keys.append('kimi_api_key')

            if 'spark_api_key' in data:
                config_manager.llm_config.spark_api_key = data['spark_api_key']
                updated_keys.append('spark_api_key')
            if 'spark_api_secret' in data:
                config_manager.llm_config.spark_api_secret = data['spark_api_secret']
                updated_keys.append('spark_api_secret')

            if 'qwen_api_key' in data:
                config_manager.llm_config.qwen_api_key = data['qwen_api_key']
                updated_keys.append('qwen_api_key')
                logger.info('🔑 [统一配置保存] 更新通义千问API Key: ****')

            if 'ernie_api_key' in data:
                config_manager.llm_config.ernie_api_key = data['ernie_api_key']
                updated_keys.append('ernie_api_key')
            if 'ernie_secret_key' in data:
                config_manager.llm_config.ernie_secret_key = data['ernie_secret_key']
                updated_keys.append('ernie_secret_key')

            if 'chatglm_api_key' in data:
                config_manager.llm_config.chatglm_api_key = data['chatglm_api_key']
                updated_keys.append('chatglm_api_key')

            if 'deepseek_api_key' in data:
                config_manager.llm_config.deepseek_api_key = data['deepseek_api_key']
                updated_keys.append('deepseek_api_key')
            
            # 保存Vision配置
            if 'gpt4v_api_key' in data:
                config_manager.vision_config.gpt4v_api_key = data['gpt4v_api_key']
                updated_keys.append('gpt4v_api_key')
            if 'gpt4v_model' in data:
                config_manager.vision_config.gpt4v_model = data['gpt4v_model']
                updated_keys.append('gpt4v_model')

            if 'claude_vision_api_key' in data:
                config_manager.vision_config.claude_vision_api_key = data['claude_vision_api_key']
                updated_keys.append('claude_vision_api_key')

            # 保存TTS配置（修正为 dataclass 中的字段名）
            if 'azure_tts_key' in data:
                config_manager.tts_model_config.azure_tts_key = data['azure_tts_key']
                updated_keys.append('azure_tts_key')
            if 'azure_tts_region' in data:
                config_manager.tts_model_config.azure_tts_region = data['azure_tts_region']
                updated_keys.append('azure_tts_region')

            logger.info(f'📝 [统一配置保存] 更新了 {len(updated_keys)} 个配置项: {updated_keys}')

            # 保存配置到文件
            logger.info('💾 [统一配置保存] 准备保存配置文件...')
            config_manager.save_config()
            logger.info('✅ [统一配置保存] 配置文件保存成功！')

            logger.info('🎉 [统一配置保存] 全部完成！')
            logger.info('=' * 80)
            return jsonify({'code': 0, 'msg': '配置保存成功', 'data': None})

        except Exception as e:
            logger.error(f'❌ [统一配置保存] 发生异常: {e}', exc_info=True)
            logger.info('=' * 80)
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    logger.info('✅ 配置管理路由注册完成')
