"""
设置管理API路由
提供用户设置、API配置的保存和加载功能
"""
import json
from flask import request, jsonify
from backend.utils.logger import logger
from pathlib import Path
from backend.core.global_state import get_global_state
from backend.config.paths import PROJECT_ROOT


def register_settings_routes(app, db_manager):
    """
    注册设置管理相关的API路由
    
    Args:
        app: Flask应用实例
        db_manager: 数据库管理器实例
    """
    
    @app.route('/api/settings', methods=['GET'])
    def get_settings():
        """获取所有设置"""
        try:
            settings = db_manager.get_settings()
            return jsonify({
                'code': 0,
                'msg': '获取成功',
                'data': settings
            })
        except Exception as e:
            logger.error(f'❌ 获取设置失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'获取失败: {str(e)}',
                'data': None
            }), 500
    
    @app.route('/api/settings', methods=['POST'])
    def save_settings():
        """保存设置"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'code': 1,
                    'msg': '设置数据不能为空',
                    'data': None
                }), 400
            
            # 保存设置到数据库
            result = db_manager.save_settings(data)
            
            if result:
                logger.info(f'✅ 保存设置成功: {len(data)}项配置')
                return jsonify({
                    'code': 0,
                    'msg': '保存成功',
                    'data': {'saved_count': len(data)}
                })
            else:
                return jsonify({
                    'code': 1,
                    'msg': '保存失败',
                    'data': None
                }), 500
                
        except Exception as e:
            logger.error(f'❌ 保存设置失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'保存失败: {str(e)}',
                'data': None
            }), 500
    
    @app.route('/api/settings/<setting_key>', methods=['GET'])
    def get_setting(setting_key):
        """获取单个设置项"""
        try:
            value = db_manager.get_setting(setting_key)
            
            logger.info(f'✅ 获取设置项成功: {setting_key}')
            
            return jsonify({
                'code': 0,
                'msg': '获取成功',
                'data': {
                    'key': setting_key,
                    'value': value
                }
            })
            
        except Exception as e:
            logger.error(f'❌ 获取设置项失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'获取失败: {str(e)}',
                'data': None
            }), 500
    
    @app.route('/api/settings/<setting_key>', methods=['PUT'])
    def update_setting(setting_key):
        """更新单个设置项"""
        try:
            data = request.get_json()
            value = data.get('value')
            
            result = db_manager.update_setting(setting_key, value)
            
            if result:
                logger.info(f'✅ 更新设置项成功: {setting_key}')
                return jsonify({
                    'code': 0,
                    'msg': '更新成功',
                    'data': {
                        'key': setting_key,
                        'value': value
                    }
                })
            else:
                return jsonify({
                    'code': 1,
                    'msg': '更新失败',
                    'data': None
                }), 500
                
        except Exception as e:
            logger.error(f'❌ 更新设置项失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'更新失败: {str(e)}',
                'data': None
            }), 500
    
    @app.route('/api/settings/api-config', methods=['POST'])
    def save_api_config():
        """保存API配置（专门用于API密钥等敏感配置）"""
        try:
            logger.info('=' * 80)
            logger.info('🔑 [API配置保存] 开始处理请求')
            data = request.get_json()
            logger.info(f'📥 [API配置保存] 接收到的数据键: {list(data.values()) if data else "空"}')
            if not data:
                logger.warning('⚠️ [API配置保存] 数据为空，拒绝请求')
                return jsonify({
                    'code': 1,
                    'msg': 'API配置数据不能为空',
                    'data': None
                }), 400

            # 过滤空值和脱敏占位值，保护已保存的真实密钥不被覆盖
            try:
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
                                logger.info(f'🙈 [API配置保存] 跳过脱敏/占位值: {k}')
                                return False
                    return True
                data = {kk: vv for kk, vv in (data or {}).items() if _should_keep(kk, vv)}
            except Exception as _e:
                logger.warning(f'⚠️ [API配置保存] 过滤占位值时出错: {_e}')

            # 1) 先写入配置文件（主路径，可靠）
            logger.info('📝 [API配置保存] 步骤1: 写入配置文件 config/ai_config.json')
            try:
                from backend.config.ai_config import get_config_manager
                cfg = get_config_manager()
                logger.info(f'✅ [API配置保存] 配置管理器加载成功')
                # LLM keys
                updated_keys = []
                if 'custom_api_key' in data:
                    cfg.llm_config.custom_api_key = data['custom_api_key']
                    updated_keys.append('custom_api_key')
                if 'custom_base_url' in data:
                    cfg.llm_config.custom_base_url = data['custom_base_url']
                    updated_keys.append('custom_base_url')
                if 'custom_model' in data:
                    cfg.llm_config.custom_model = data['custom_model']
                    updated_keys.append('custom_model')
                logger.info(f'📝 [API配置保存] 更新了 {len(updated_keys)} 个LLM配置项: {updated_keys}')

                # Vision keys
                if 'gpt4v_api_key' in data:
                    cfg.vision_config.gpt4v_api_key = data['gpt4v_api_key']
                    updated_keys.append('gpt4v_api_key')
                if 'gpt4v_model' in data:
                    cfg.vision_config.gpt4v_model = data['gpt4v_model']
                    updated_keys.append('gpt4v_model')
                if 'claude_vision_api_key' in data:
                    cfg.vision_config.claude_vision_api_key = data['claude_vision_api_key']
                    updated_keys.append('claude_vision_api_key')
                if 'gemini_vision_api_key' in data:
                    cfg.vision_config.gemini_vision_api_key = data['gemini_vision_api_key']
                    updated_keys.append('gemini_vision_api_key')
                
                # TTS
                if 'azure_tts_key' in data:
                    cfg.tts_model_config.azure_tts_key = data['azure_tts_key']
                    updated_keys.append('azure_tts_key')
                if 'azure_tts_region' in data:
                    cfg.tts_model_config.azure_tts_region = data['azure_tts_region']
                    updated_keys.append('azure_tts_region')
                if 'enable_voice_clone' in data:
                    val = data['enable_voice_clone']
                    if isinstance(val, str):
                        cfg.tts_model_config.enable_voice_clone = val.lower() not in ('0', 'false', 'off', 'no')
                    else:
                        cfg.tts_model_config.enable_voice_clone = bool(val)
                    updated_keys.append('enable_voice_clone')
                if 'voice_clone_model_path' in data:
                    cfg.tts_model_config.voice_clone_model_path = data['voice_clone_model_path']
                    updated_keys.append('voice_clone_model_path')
                if 'voice_clone_executable_path' in data:
                    cfg.tts_model_config.voice_clone_executable_path = data['voice_clone_executable_path']
                    updated_keys.append('voice_clone_executable_path')

                logger.info(f'💾 [API配置保存] 准备保存配置文件...')
                cfg.save_config()
                logger.info(f'✅ [API配置保存] 配置文件保存成功！')
            except Exception as ie:
                logger.error(f'❌ [API配置保存] 写入配置文件失败: {ie}', exc_info=True)
                logger.warning(f'⚠️ [API配置保存] 继续尝试保存到数据库...')

            # 2) 尝试写入数据库（可选失败不阻断）
            logger.info('📝 [API配置保存] 步骤2: 写入数据库')
            try:
                db_manager.save_api_config(data)
                logger.info(f'✅ [API配置保存] 数据库保存成功！')
            except Exception as de:
                logger.error(f'❌ [API配置保存] 保存到数据库失败: {de}', exc_info=True)

            logger.info(f'🎉 [API配置保存] 全部完成！保存的键: {list(data.keys())}')
            logger.info('=' * 80)
            return jsonify({
                'code': 0,
                'msg': 'API配置保存成功',
                'data': {'saved_keys': list(data.keys())}
            })

        except Exception as e:
            logger.error(f'❌ [API配置保存] 发生异常: {e}', exc_info=True)
            logger.info('=' * 80)
            return jsonify({
                'code': 1,
                'msg': f'保存失败: {str(e)}',
                'data': None
            }), 500
    
    @app.route('/api/settings/api-config', methods=['GET'])
    def get_api_config():
        """获取API配置"""
        try:
            # 1) 从配置文件读取（确保重启后仍能取到值）
            file_conf = {}
            try:
                from backend.config.ai_config import get_config_manager
                cfg = get_config_manager()
                file_conf = {
                    # LLM
                    'custom_api_key': getattr(cfg.llm_config, 'custom_api_key', ''),
                    'custom_base_url': getattr(cfg.llm_config, 'custom_base_url', ''),
                    'custom_model': getattr(cfg.llm_config, 'custom_model', ''),
                    # Vision
                    'gpt4v_api_key': getattr(cfg.vision_config, 'gpt4v_api_key', ''),
                    'gpt4v_model': getattr(cfg.vision_config, 'gpt4v_model', ''),
                    'claude_vision_api_key': getattr(cfg.vision_config, 'claude_vision_api_key', ''),
                    'gemini_vision_api_key': getattr(cfg.vision_config, 'gemini_vision_api_key', ''),
                    'openai_vision_api_key': getattr(cfg.vision_config, 'openai_vision_api_key', ''),
                    'default_vision_model': getattr(cfg.vision_config, 'default_model', ''),
                    # TTS（兼容命名）
                    'azure_tts_key': getattr(cfg.tts_model_config, 'azure_tts_key', '') or getattr(cfg.tts_model_config, 'azure_subscription_key', ''),
                    'azure_tts_region': getattr(cfg.tts_model_config, 'azure_tts_region', '') or getattr(cfg.tts_model_config, 'azure_region', ''),
                    'enable_voice_clone': getattr(cfg.tts_model_config, 'enable_voice_clone', False),
                    'voice_clone_model_path': getattr(cfg.tts_model_config, 'voice_clone_model_path', ''),
                    'voice_clone_executable_path': getattr(cfg.tts_model_config, 'voice_clone_executable_path', ''),
                }
            except Exception:
                pass

            # 2) 合并数据库配置（若有值则覆盖文件值）
            try:
                db_conf = db_manager.get_api_config() or {}
            except Exception:
                db_conf = {}
            merged = dict(file_conf)
            merged.update(db_conf)

            # 3) 脱敏
            for key, value in list(merged.items()):
                if not isinstance(key, str):
                    continue
                kl = key.lower()
                sensitive = ('api_key' in kl) or ('secret' in kl) or (key in ('azure_tts_key', 'azure_subscription_key'))
                if isinstance(value, str) and sensitive:
                    if value and len(value) > 8:
                        merged[key] = value[:4] + '*' * (len(value) - 8) + value[-4:]

            logger.info('🔑 获取API配置成功（文件+DB合并）')
            return jsonify({'code': 0, 'msg': '获取成功', 'data': merged})
            
        except Exception as e:
            logger.error(f'❌ 获取API配置失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'获取失败: {str(e)}',
                'data': None
            }), 500

    @app.route('/api/settings/azure-tts-preview', methods=['POST'])
    def azure_tts_preview():
        """生成 Azure TTS 试听音频"""
        try:
            data = request.get_json() or {}
            voice_id = (data.get('voice_id') or '').strip() or 'zh-CN-XiaoxiaoNeural'
            text = (data.get('text') or '').strip() or '这是 Azure TTS 试听示例，您好！'

            gs = get_global_state()
            tts_engine = gs.get_tts_engine() if gs else None
            if not tts_engine or 'azure' not in (tts_engine.available_engines or []):
                return jsonify({
                    'code': 1,
                    'msg': 'Azure TTS 未正确配置，请先在设置中填写密钥和区域并保存。',
                    'data': None
                }), 400

            preview_dir = PROJECT_ROOT / 'output' / 'previews'
            preview_dir.mkdir(parents=True, exist_ok=True)
            safe_voice = voice_id.replace('/', '_').replace('\\', '_')
            output_path = preview_dir / f'azure_preview_{safe_voice}.mp3'

            ok = tts_engine.synthesize(
                text=text,
                output_path=str(output_path),
                engine='azure',
                voice=voice_id
            )
            if not ok:
                return jsonify({
                    'code': 1,
                    'msg': 'Azure TTS 试听生成失败，请检查密钥、区域或网络。',
                    'data': None
                }), 500

            p = Path(str(output_path)).resolve()
            try:
                rel = p.relative_to(PROJECT_ROOT)
                rel_str = str(rel).replace('\\', '/')
            except Exception:
                rel_str = f"output/previews/{p.name}"
            audio_url = '/' + rel_str.lstrip('/')

            return jsonify({
                'code': 0,
                'msg': '试听生成成功',
                'data': {
                    'audio_path': rel_str,
                    'audio_url': audio_url
                }
            })
        except Exception as e:
            logger.error(f'❌ Azure TTS 试听生成失败: {e}', exc_info=True)
            return jsonify({
                'code': 1,
                'msg': f'试听失败: {str(e)}',
                'data': None
            }), 500

    @app.route('/api/settings/test-api', methods=['POST'])
    def test_api_connection():
        """测试API连接 - 真实HTTP连通校验（尽量无副作用）"""
        try:
            import time as _time
            import requests
            data = request.get_json() or {}
            api_type = str(data.get('api_type') or '').lower()
            api_key = data.get('api_key') or ''
            base_url = data.get('base_url') or ''
            extra = data.get('extra') or {}

            # 若未显式传入 api_key，则从配置文件兜底读取
            if not api_key:
                try:
                    from backend.config.ai_config import get_config_manager
                    cfg = get_config_manager()
                    m = api_type
                    if m in ('custom'):
                        api_key = getattr(cfg.llm_config, 'custom_api_key', '')
                        if not base_url:
                            base_url = getattr(cfg.llm_config, 'custom_base_url', '')
                    elif m in ('claude','claude-vision','anthropic'):
                        api_key = getattr(cfg.llm_config, 'anthropic_api_key', '')
                    elif m == 'gemini':
                        api_key = getattr(cfg.llm_config, 'gemini_api_key', '')
                    elif m in ('qwen','tongyi'):
                        api_key = getattr(cfg.llm_config, 'qwen_api_key', '') or getattr(cfg.llm_config, 'tongyi_api_key', '')
                    elif m in ('ernie','wenxin'):
                        ak = getattr(cfg.llm_config, 'ernie_api_key', '')
                        sk = getattr(cfg.llm_config, 'ernie_secret_key', '')
                        if ak and sk:
                            api_key = f'{ak}:{sk}'
                    elif m in ('chatglm','zhipu'):
                        api_key = getattr(cfg.llm_config, 'chatglm_api_key', '')
                    elif m == 'deepseek':
                        api_key = getattr(cfg.llm_config, 'deepseek_api_key', '')
                    elif m in ('azure-tts','azure'):
                        api_key = getattr(cfg.tts_model_config, 'azure_tts_key', '') or getattr(cfg.tts_model_config, 'azure_subscription_key', '')
                        if not extra.get('region'):
                            extra['region'] = getattr(cfg.tts_model_config, 'azure_tts_region', '') or getattr(cfg.tts_model_config, 'azure_region', '')
                except Exception:
                    pass

            if not api_type:
                return jsonify({'code': 1, 'msg': '缺少参数: api_type', 'data': None}), 400

            # helper
            def ok(latency, status=200, detail='OK'):
                return jsonify({
                    'code': 0,
                    'msg': '连接成功',
                    'data': {
                        'api_type': api_type,
                        'status': 'connected',
                        'http_status': status,
                        'latency_ms': int(latency * 1000),
                        'detail': detail
                    }
                })

            def _format_http_error(status: int, body_snippet: str) -> str:
                """根据HTTP状态码和返回内容生成更友好的错误说明"""
                try:
                    txt = (body_snippet or '').strip()
                except Exception:
                    txt = ''

                # 基础前缀：按状态码归类
                if status in (401, 403):
                    prefix = f'鉴权失败（HTTP {status}），请检查 API Key/Secret 是否正确、是否有对应权限。'
                elif 400 <= status < 500:
                    prefix = f'请求配置可能有误（HTTP {status}），请检查模型名称、Base URL 等参数。'
                elif 500 <= status < 600:
                    prefix = f'服务端异常（HTTP {status}），可能是目标服务不稳定或限流，请稍后重试。'
                else:
                    prefix = f'请求失败（HTTP {status}）。'

                if txt:
                    # 附上服务端返回的关键片段，便于快速定位问题
                    return f"{prefix} 服务器返回：{txt}"
                return prefix

            def err(status, detail):
                msg = _format_http_error(status, detail)
                return jsonify({
                    'code': 1,
                    'msg': msg,
                    'data': {
                        'api_type': api_type,
                        'status': 'error',
                        'http_status': status,
                        'detail': detail
                    }
                }), 200

            timeout = float(extra.get('timeout', 5))
            t0 = _time.perf_counter()

            # custom
            if api_type in ('custom'):
                url = (base_url.rstrip('/') if base_url else 'https://dashscope.aliyuncs.com/compatible-mode/v1') + '/models'
                headers = {'Authorization': f'Bearer {api_key}'}
                r = requests.get(url, headers=headers, timeout=timeout)
                if r.status_code == 200:
                    return ok(_time.perf_counter()-t0, r.status_code)
                return err(r.status_code, r.text[:300])

            # Anthropic / Claude / Claude Vision
            if api_type in ('claude', 'claude-vision'):
                url = 'https://api.anthropic.com/v1/models'
                headers = {'x-api-key': api_key, 'anthropic-version': '2023-06-01'}
                r = requests.get(url, headers=headers, timeout=timeout)
                if r.status_code == 200:
                    return ok(_time.perf_counter()-t0, r.status_code)
                return err(r.status_code, r.text[:300])

            # Google Gemini
            if api_type == 'gemini':
                url = f'https://generativelanguage.googleapis.com/v1/models?key={api_key}'
                r = requests.get(url, timeout=timeout)
                if r.status_code == 200:
                    return ok(_time.perf_counter()-t0, r.status_code)
                return err(r.status_code, r.text[:300])

            # DeepSeek
            if api_type == 'deepseek':
                url = 'https://api.deepseek.com/v1/models'
                headers = {'Authorization': f'Bearer {api_key}'}
                r = requests.get(url, headers=headers, timeout=timeout)
                if r.status_code == 200:
                    return ok(_time.perf_counter()-t0, r.status_code)
                return err(r.status_code, r.text[:300])

            # Kimi (Moonshot)
            if api_type == 'kimi':
                url = 'https://api.moonshot.cn/v1/models'
                headers = {'Authorization': f'Bearer {api_key}'}
                r = requests.get(url, headers=headers, timeout=timeout)
                if r.status_code == 200:
                    return ok(_time.perf_counter()-t0, r.status_code)
                return err(r.status_code, r.text[:300])

            # 通义千问 (DashScope)
            if api_type in ('qwen', 'tongyi'):
                # 模型列表接口在不同版本有差异，这里优先尝试 /api/v1/models
                url = 'https://dashscope.aliyuncs.com/api/v1/models'
                headers = {'Authorization': f'Bearer {api_key}'}
                r = requests.get(url, headers=headers, timeout=timeout)
                if r.status_code in (200, 401, 403):  # 401/403 也代表网络可达与Key已校验
                    if r.status_code == 200:
                        return ok(_time.perf_counter()-t0, r.status_code)
                    return err(r.status_code, r.text[:300])
                return err(r.status_code, r.text[:300])

            # 文心一言 (Baidu) - 仅获取access_token校验
            if api_type in ('ernie', 'wenxin'):
                try:
                    ak, sk = (api_key.split(':', 1) + [''])[:2]
                except Exception:
                    ak, sk = api_key, ''
                if not ak or not sk:
                    return err(400, '需要传入 "api_key:secret_key"')
                token_url = f'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={ak}&client_secret={sk}'
                r = requests.get(token_url, timeout=timeout)
                if r.status_code == 200 and 'access_token' in r.text:
                    return ok(_time.perf_counter()-t0, r.status_code)
                return err(r.status_code, r.text[:300])

            # ChatGLM (Zhipu)
            if api_type in ('chatglm', 'zhipu'):
                url = 'https://open.bigmodel.cn/api/paas/v4/models'
                headers = {'Authorization': f'Bearer {api_key}'}
                r = requests.get(url, headers=headers, timeout=timeout)
                if r.status_code in (200, 401, 403):
                    if r.status_code == 200:
                        return ok(_time.perf_counter()-t0, r.status_code)
                    return err(r.status_code, r.text[:300])
                return err(r.status_code, r.text[:300])

            # Azure TTS - 列出可用声音
            if api_type in ('azure-tts', 'azure'):
                region = (extra.get('region') or '').strip() or 'eastus'
                url = f'https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list'
                headers = {'Ocp-Apim-Subscription-Key': api_key}
                r = requests.get(url, headers=headers, timeout=timeout)
                if r.status_code == 200:
                    return ok(_time.perf_counter()-t0, r.status_code, f'{len(r.json())} voices')
                return err(r.status_code, r.text[:300])

            return jsonify({'code': 1, 'msg': f'不支持的api_type: {api_type}', 'data': None}), 400

        except Exception as e:
            logger.error(f'❌ 测试API连接失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'测试失败: {str(e)}', 'data': None}), 500

    @app.route('/api/settings/reset', methods=['POST'])
    def reset_all_settings():
        """恢复所有设置为默认值（删除settings表中记录）"""
        try:
            conn = db_manager.get_connection()
            cur = conn.cursor()
            cur.execute('DELETE FROM settings')
            conn.commit()
            return jsonify({'code': 0, 'msg': '重置成功', 'data': None})
        except Exception as e:
            logger.error(f'❌ 重置设置失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'重置失败: {str(e)}', 'data': None}), 500
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @app.route('/api/settings/clear-cache', methods=['POST'])
    def clear_cache():
        """清理临时缓存目录"""
        try:
            from backend.config.paths import clean_temp_dir
            clean_temp_dir()
            return jsonify({'code': 0, 'msg': '清理成功', 'data': None})
        except Exception as e:
            logger.error(f'❌ 清理缓存失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'清理失败: {str(e)}', 'data': None}), 500

    @app.route('/api/update/check', methods=['GET'])
    def check_update():
        """检查更新

        当前未集成远程更新服务，因此只返回本地版本信息，并提示无在线更新。
        """
        try:
            try:
                # 优先从 backend 包中获取版本号
                from backend import __version__ as backend_version
                current_version = str(backend_version)
            except Exception:
                # 兜底版本号
                current_version = '2.0.0'

            data = {
                'hasUpdate': False,
                'version': current_version,
                'notes': '当前安装版本为本地构建，尚未配置远程更新服务。如需升级，请关注项目发布页或手动下载安装新版。'
            }
            return jsonify({'code': 0, 'msg': '获取成功', 'data': data})
        except Exception as e:
            logger.error(f'❌ 检查更新失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'检查失败: {str(e)}', 'data': None}), 500

    @app.route('/api/update/download', methods=['POST'])
    def download_update():
        """下载更新

        当前未配置在线更新/下载通道，接口仅返回说明信息，不提供虚构下载链接。
        """
        try:
            return jsonify({
                'code': 1,
                'msg': '当前版本未集成自动更新通道，请前往项目发布页手动下载最新安装包。',
                'data': {
                    'downloadUrl': None
                }
            })
        except Exception as e:
            logger.error(f'❌ 下载更新失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': f'下载失败: {str(e)}', 'data': None}), 500

    logger.info('✅ 设置管理API路由注册完成')
