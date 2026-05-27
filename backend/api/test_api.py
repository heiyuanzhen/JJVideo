#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试API路由 - 用于测试各AI模型连接
"""

from flask import jsonify, request
from loguru import logger
import requests
import time
import os


def register_test_routes(app, config_manager):
    """
    注册所有测试API路由
    
    Args:
        app: Flask应用实例
        config_manager: 配置管理器实例
    """
    
    @app.route('/api/test/custom', methods=['POST'])
    def test_custom():
        """测试Custom API连接"""
        try:
            data = request.get_json()
            api_key = data.get('api_key')
            base_url = data.get('base_url')
            model = data.get('model')
            
            if not api_key:
                return jsonify({'code': 1, 'msg': 'API Key不能为空', 'data': None}), 400
            
            logger.info(f'🧪 测试Custom连接: {model}')
            
            # 测试API连接
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            test_data = {
                'model': model,
                'messages': [{'role': 'user', 'content': 'Hello'}],
                'max_tokens': 10
            }
            response = requests.post(
                f'{base_url}/chat/completions',
                headers=headers,
                json=test_data,
                timeout=10
            )
            if response.status_code == 200:
                logger.info('✅ Custom连接测试成功')
                return jsonify({
                    'code': 0,
                    'msg': 'Custom连接测试成功！',
                    'data': {'model': model, 'status': 'success'}
                })
            else:
                logger.error(f'❌ Custom测试失败: {response.status_code}')
                return jsonify({
                    'code': 1,
                    'msg': f'连接失败: {response.text}',
                    'data': None
                }), 400
        except Exception as e:
            logger.error(f'❌ Custom测试异常: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    
    @app.route('/api/test/anthropic', methods=['POST'])
    @app.route('/api/test/claude', methods=['POST'])
    def test_anthropic():
        """测试Anthropic Claude API连接"""
        try:
            data = request.get_json()
            api_key = data.get('api_key')
            model = data.get('model', 'claude-3-sonnet-20240229')
            
            if not api_key:
                return jsonify({'code': 1, 'msg': 'API Key不能为空', 'data': None}), 400
            
            logger.info(f'🧪 测试Claude连接: {model}')
            
            headers = {
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json'
            }
            
            test_data = {
                'model': model,
                'messages': [{'role': 'user', 'content': 'Hello'}],
                'max_tokens': 10
            }
            
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers,
                json=test_data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info('✅ Claude连接测试成功')
                return jsonify({
                    'code': 0,
                    'msg': 'Claude连接测试成功！',
                    'data': {'model': model, 'status': 'success'}
                })
            else:
                logger.error(f'❌ Claude测试失败: {response.status_code}')
                return jsonify({
                    'code': 1,
                    'msg': f'连接失败: {response.text}',
                    'data': None
                }), 400
                
        except Exception as e:
            logger.error(f'❌ Claude测试异常: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    
    @app.route('/api/test/gemini', methods=['POST'])
    def test_gemini():
        """测试Google Gemini API连接"""
        try:
            data = request.get_json()
            api_key = data.get('api_key')
            
            if not api_key:
                return jsonify({'code': 1, 'msg': 'API Key不能为空', 'data': None}), 400
            
            logger.info('🧪 测试Gemini连接')
            
            # 简化测试 - 验证API Key格式
            if len(api_key) < 10:
                return jsonify({
                    'code': 1,
                    'msg': 'API Key格式不正确（本地格式检查，未实际请求Gemini接口）',
                    'data': None
                }), 400
            
            logger.info('✅ Gemini API Key本地格式检查通过（未实际请求Gemini接口）')
            return jsonify({
                'code': 0,
                'msg': 'Gemini API Key本地格式检查通过（未实际请求Gemini接口）',
                'data': {'status': 'local_validation_only'}
            })
                
        except Exception as e:
            logger.error(f'❌ Gemini测试异常: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    
    @app.route('/api/test/kimi', methods=['POST'])
    def test_kimi():
        """测试月之暗面 Kimi API连接"""
        try:
            data = request.get_json()
            api_key = data.get('api_key')
            
            if not api_key:
                return jsonify({'code': 1, 'msg': 'API Key不能为空', 'data': None}), 400
            
            logger.info('🧪 测试Kimi连接')
            
            logger.info('✅ Kimi API Key本地检查通过（仅校验是否为空，未实际请求Kimi接口）')
            return jsonify({
                'code': 0,
                'msg': 'Kimi API Key本地检查通过（仅校验是否为空，未实际请求Kimi接口）',
                'data': {'status': 'local_validation_only'}
            })
                
        except Exception as e:
            logger.error(f'❌ Kimi测试异常: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    
    @app.route('/api/test/spark', methods=['POST'])
    def test_spark():
        """测试讯飞星火API连接"""
        try:
            data = request.get_json()
            api_key = data.get('api_key')
            api_secret = data.get('api_secret')
            
            if not api_key or not api_secret:
                return jsonify({'code': 1, 'msg': 'API Key和Secret不能为空', 'data': None}), 400
            
            logger.info('🧪 测试讯飞星火连接')
            
            logger.info('✅ 讯飞星火API凭证本地检查通过（仅校验是否为空，未实际请求星火接口）')
            return jsonify({
                'code': 0,
                'msg': '讯飞星火API凭证本地检查通过（仅校验是否为空，未实际请求星火接口）',
                'data': {'status': 'local_validation_only'}
            })
                
        except Exception as e:
            logger.error(f'❌ 讯飞星火测试异常: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    
    @app.route('/api/test/qwen', methods=['POST'])
    def test_qwen():
        """测试通义千问API连接"""
        try:
            data = request.get_json()
            api_key = data.get('api_key')
            
            if not api_key:
                return jsonify({'code': 1, 'msg': 'API Key不能为空', 'data': None}), 400
            
            logger.info('🧪 测试通义千问连接')
            
            logger.info('✅ 通义千问API Key本地检查通过（仅校验是否为空，未实际请求通义千问接口）')
            return jsonify({
                'code': 0,
                'msg': '通义千问API Key本地检查通过（仅校验是否为空，未实际请求通义千问接口）',
                'data': {'status': 'local_validation_only'}
            })
                
        except Exception as e:
            logger.error(f'❌ 通义千问测试异常: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    
    @app.route('/api/test/ernie', methods=['POST'])
    def test_ernie():
        """测试百度文心一言API连接"""
        try:
            data = request.get_json()
            api_key = data.get('api_key')
            secret_key = data.get('secret_key')
            
            if not api_key or not secret_key:
                return jsonify({'code': 1, 'msg': 'API Key和Secret Key不能为空', 'data': None}), 400
            
            logger.info('🧪 测试文心一言连接')
            
            logger.info('✅ 文心一言API凭证本地检查通过（仅校验是否为空，未实际请求文心一言接口）')
            return jsonify({
                'code': 0,
                'msg': '文心一言API凭证本地检查通过（仅校验是否为空，未实际请求文心一言接口）',
                'data': {'status': 'local_validation_only'}
            })
                
        except Exception as e:
            logger.error(f'❌ 文心一言测试异常: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    
    @app.route('/api/test/chatglm', methods=['POST'])
    def test_chatglm():
        """测试智谱ChatGLM API连接"""
        try:
            data = request.get_json()
            api_key = data.get('api_key')
            
            if not api_key:
                return jsonify({'code': 1, 'msg': 'API Key不能为空', 'data': None}), 400
            
            logger.info('🧪 测试ChatGLM连接')
            
            logger.info('✅ ChatGLM API Key本地检查通过（仅校验是否为空，未实际请求ChatGLM接口）')
            return jsonify({
                'code': 0,
                'msg': 'ChatGLM API Key本地检查通过（仅校验是否为空，未实际请求ChatGLM接口）',
                'data': {'status': 'local_validation_only'}
            })
                
        except Exception as e:
            logger.error(f'❌ ChatGLM测试异常: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    
    @app.route('/api/test/deepseek', methods=['POST'])
    def test_deepseek():
        """测试DeepSeek API连接"""
        try:
            data = request.get_json()
            api_key = data.get('api_key')
            
            if not api_key:
                return jsonify({'code': 1, 'msg': 'API Key不能为空', 'data': None}), 400
            
            logger.info('🧪 测试DeepSeek连接')
            
            logger.info('✅ DeepSeek API Key本地检查通过（仅校验是否为空，未实际请求DeepSeek接口）')
            return jsonify({
                'code': 0,
                'msg': 'DeepSeek API Key本地检查通过（仅校验是否为空，未实际请求DeepSeek接口）',
                'data': {'status': 'local_validation_only'}
            })
                
        except Exception as e:
            logger.error(f'❌ DeepSeek测试异常: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    
    @app.route('/api/test/gpt4v', methods=['POST'])
    def test_gpt4v():
        """测试GPT-4V API连接"""
        try:
            data = request.get_json()
            api_key = data.get('api_key')
            model = data.get('model', 'gpt-4-vision-preview')
            
            if not api_key:
                return jsonify({'code': 1, 'msg': 'API Key不能为空', 'data': None}), 400

            logger.info('🧪 测试GPT-4V连接（本地检查，仅校验是否为空，未实际请求GPT-4V接口）')

            logger.info('✅ GPT-4V API Key本地检查通过（未实际请求GPT-4V接口）')
            return jsonify({
                'code': 0,
                'msg': 'GPT-4V API Key本地检查通过（仅校验是否为空，未实际请求GPT-4V接口）',
                'data': {'model': model, 'status': 'local_validation_only'}
            })
                
        except Exception as e:
            logger.error(f'❌ GPT-4V测试异常: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    
    @app.route('/api/test/claude-vision', methods=['POST'])
    def test_claude_vision():
        """测试Claude Vision API连接"""
        try:
            data = request.get_json()
            api_key = data.get('api_key')
            
            if not api_key:
                return jsonify({'code': 1, 'msg': 'API Key不能为空', 'data': None}), 400

            logger.info('🧪 测试Claude Vision连接（本地检查，仅校验是否为空，未实际请求Claude Vision接口）')

            logger.info('✅ Claude Vision API Key本地检查通过（未实际请求Claude Vision接口）')
            return jsonify({
                'code': 0,
                'msg': 'Claude Vision API Key本地检查通过（仅校验是否为空，未实际请求Claude Vision接口）',
                'data': {'status': 'local_validation_only'}
            })
                
        except Exception as e:
            logger.error(f'❌ Claude Vision测试异常: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500
    
    
    @app.route('/api/test/azure-tts', methods=['POST'])
    def test_azure_tts():
        """测试Azure TTS API连接"""
        try:
            data = request.get_json()
            subscription_key = data.get('subscription_key')
            region = data.get('region', 'eastus')
            
            if not subscription_key:
                return jsonify({'code': 1, 'msg': 'Subscription Key不能为空', 'data': None}), 400

            logger.info('🧪 测试Azure TTS连接（本地检查，仅校验是否为空，未实际请求Azure TTS接口）')

            logger.info('✅ Azure TTS凭证本地检查通过（未实际请求Azure TTS接口）')
            return jsonify({
                'code': 0,
                'msg': 'Azure TTS凭证本地检查通过（仅校验是否为空，未实际请求Azure TTS接口）',
                'data': {'region': region, 'status': 'local_validation_only'}
            })
                
        except Exception as e:
            logger.error(f'❌ Azure TTS测试异常: {e}')
            return jsonify({'code': 1, 'msg': str(e), 'data': None}), 500


    @app.route('/api/test/voice-clone-engine', methods=['POST'])
    def test_voice_clone_engine():
        """测试本地 Voice Clone 引擎配置（仅检查路径和执行权限，不真正推理）"""
        try:
            try:
                from backend.config.ai_config import get_config_manager
                cfg = get_config_manager()
                model_path = getattr(cfg.tts_model_config, 'voice_clone_model_path', '')
                exe_path = getattr(cfg.tts_model_config, 'voice_clone_executable_path', '')
            except Exception as e:
                logger.error(f'❌ 读取 Voice Clone 配置失败: {e}', exc_info=True)
                return jsonify({'code': 1, 'msg': f'读取配置失败: {e}', 'data': None}), 200

            issues = []

            # 检查模型路径
            if not model_path:
                issues.append('模型路径未配置（voice_clone_model_path 为空）')
            elif not os.path.exists(model_path):
                issues.append(f'模型路径不存在: {model_path}')
            elif not os.path.isdir(model_path):
                issues.append(f'模型路径不是目录: {model_path}')

            # 检查可执行文件路径
            if not exe_path:
                issues.append('可执行文件路径未配置（voice_clone_executable_path 为空）')
            elif not os.path.exists(exe_path):
                issues.append(f'可执行文件不存在: {exe_path}')
            elif not os.path.isfile(exe_path):
                issues.append(f'可执行文件路径不是文件: {exe_path}')
            elif not os.access(exe_path, os.X_OK):
                issues.append(f'可执行文件没有执行权限: {exe_path}')

            if issues:
                logger.warning('⚠️ Voice Clone 引擎配置存在问题: ' + ' | '.join(issues))
                return jsonify({'code': 1, 'msg': 'Voice Clone 引擎配置异常', 'data': {'details': issues}}), 200

            logger.info('✅ Voice Clone 引擎配置检测通过')
            return jsonify({'code': 0, 'msg': 'Voice Clone 引擎配置正常', 'data': {'details': ['模型路径和可执行文件路径均有效。']}}), 200

        except Exception as e:
            logger.error(f'❌ Voice Clone 引擎测试异常: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'测试失败: {str(e)}', 'data': None}), 500
    
    
    logger.info('✅ 测试API路由注册完成 (13个)')
