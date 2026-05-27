# -*- coding: utf-8 -*-
"""
Voice Clone API
语音克隆API - 完整实现
"""

import logging
import time
from pathlib import Path
from flask import Blueprint, request, jsonify
from backend.config.paths import PROJECT_ROOT, OUTPUTS_DIR
from backend.core.global_state import get_global_state
from backend.config.ai_config import get_config_manager

logger = logging.getLogger(__name__)

voice_clone_bp = Blueprint('voice_clone', __name__)
voice_clone_engine = None


def register_voice_clone_routes(app, vc_engine):
    """注册语音克隆API路由"""
    global voice_clone_engine
    voice_clone_engine = vc_engine
    app.register_blueprint(voice_clone_bp, url_prefix='/api/voice-clone')
    logger.info('✅ 语音克隆API路由注册完成')


@voice_clone_bp.route('/health', methods=['GET'])
def voice_clone_health():
    """语音克隆健康检查

    返回是否启用、配置是否完整、引擎是否就绪等信息，便于前端或脚本快速诊断。
    """
    try:
        cfg = get_config_manager()
        enabled = getattr(cfg.tts_model_config, 'enable_voice_clone', False)
        model_path = getattr(cfg.tts_model_config, 'voice_clone_model_path', '') or ''
        exe_path = getattr(cfg.tts_model_config, 'voice_clone_executable_path', '') or ''

        engine_initialized = voice_clone_engine is not None
        engine_status = None
        engine_ready = False

        if engine_initialized:
            try:
                engine_status = voice_clone_engine.get_status()
                engine_ready = bool(engine_status.get('ready'))
            except Exception as e:
                logger.error(f'检查 Voice Clone 引擎状态失败: {e}', exc_info=True)

        data = {
            'enabled': bool(enabled),
            'engine_initialized': engine_initialized,
            'engine_status': engine_status,
            'config': {
                'model_path': model_path,
                'executable_path': exe_path,
            }
        }
        data['ready'] = bool(data['enabled'] and engine_initialized and engine_ready)

        msg = 'Voice Clone 已启用' if data['enabled'] else 'Voice Clone 未启用'
        return jsonify({'code': 0, 'msg': msg, 'data': data})

    except Exception as e:
        logger.error(f'❌ Voice Clone 健康检查失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'健康检查失败: {str(e)}', 'data': None}), 500


@voice_clone_bp.route('/builtin-voices', methods=['GET'])
def get_builtin_voices():
    """获取内置音色列表"""
    try:
        voices = voice_clone_engine.get_builtin_voices()
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': voices
        })
    except Exception as e:
        logger.error(f'获取内置音色失败: {e}', exc_info=True)
        return jsonify({
            'code': 1,
            'msg': f'获取失败: {str(e)}',
            'data': None
        }), 500


@voice_clone_bp.route('/clone', methods=['POST'])
def clone_voice():
    """克隆语音"""
    try:
        data = request.get_json()
        
        if not data or 'source_audio' not in data or 'target_voice' not in data:
            return jsonify({
                'code': 1,
                'msg': '参数错误：缺少必需参数',
                'data': None
            }), 400
        
        output_path = voice_clone_engine.clone_voice(
            source_audio=data['source_audio'],
            target_voice=data['target_voice'],
            output_path=data.get('output_path'),
            save_tone=data.get('save_tone', False)
        )
        
        if output_path:
            return jsonify({
                'code': 0,
                'msg': '克隆成功',
                'data': {'output_path': output_path}
            })
        else:
            return jsonify({
                'code': 1,
                'msg': '克隆失败',
                'data': None
            }), 500
            
    except Exception as e:
        logger.error(f'克隆语音失败: {e}', exc_info=True)
        return jsonify({
            'code': 1,
            'msg': f'克隆失败: {str(e)}',
            'data': None
        }), 500


@voice_clone_bp.route('/batch-clone', methods=['POST'])
def batch_clone():
    """批量克隆语音"""
    try:
        data = request.get_json()
        
        if not data or 'source_audios' not in data or 'target_voice' not in data:
            return jsonify({
                'code': 1,
                'msg': '参数错误：缺少必需参数',
                'data': None
            }), 400
        
        output_paths = voice_clone_engine.batch_clone_voice(
            source_audios=data['source_audios'],
            target_voice=data['target_voice'],
            output_dir=data.get('output_dir'),
            save_tone=data.get('save_tone', False)
        )
        
        return jsonify({
            'code': 0,
            'msg': '批量克隆完成',
            'data': {'output_paths': output_paths}
        })
        
    except Exception as e:
        logger.error(f'批量克隆失败: {e}', exc_info=True)
        return jsonify({
            'code': 1,
            'msg': f'批量克隆失败: {str(e)}',
            'data': None
        }), 500


@voice_clone_bp.route('/extract-tone', methods=['POST'])
def extract_tone():
    """提取音色特征"""
    try:
        data = request.get_json()
        
        if not data or 'audio_path' not in data:
            return jsonify({
                'code': 1,
                'msg': '参数错误：缺少音频路径',
                'data': None
            }), 400
        
        tone_file = voice_clone_engine.extract_tone(data['audio_path'])
        
        if tone_file:
            return jsonify({
                'code': 0,
                'msg': '提取成功',
                'data': {'tone_file': tone_file}
            })
        else:
            return jsonify({
                'code': 1,
                'msg': '提取失败',
                'data': None
            }), 500
            
    except Exception as e:
        logger.error(f'提取音色失败: {e}', exc_info=True)
        return jsonify({
            'code': 1,
            'msg': f'提取失败: {str(e)}',
            'data': None
        }), 500


@voice_clone_bp.route('/clone-custom', methods=['POST'])
def clone_with_custom():
    """使用自定义音色克隆"""
    try:
        data = request.get_json()
        
        if not data or 'source_audio' not in data or 'reference_voice' not in data:
            return jsonify({
                'code': 1,
                'msg': '参数错误：缺少必需参数',
                'data': None
            }), 400
        
        output_path = voice_clone_engine.clone_with_custom_voice(
            source_audio=data['source_audio'],
            reference_voice=data['reference_voice'],
            output_path=data.get('output_path')
        )
        
        if output_path:
            return jsonify({
                'code': 0,
                'msg': '克隆成功',
                'data': {'output_path': output_path}
            })
        else:
            return jsonify({
                'code': 1,
                'msg': '克隆失败',
                'data': None
            }), 500
            
    except Exception as e:
        logger.error(f'自定义音色克隆失败: {e}', exc_info=True)
        return jsonify({
            'code': 1,
            'msg': f'克隆失败: {str(e)}',
            'data': None
        }), 500


@voice_clone_bp.route('/tts-generate', methods=['POST'])
def tts_generate_clone():
    """文本→TTS→本地 Voice Clone 一体化生成"""
    try:
        data = request.get_json() or {}
        text = (data.get('text') or '').strip()
        if not text:
            return jsonify({'code': 1, 'msg': '参数错误：缺少文本', 'data': None}), 400

        # 文本长度限制：默认不限制，只有显式传入 max_text_length 才校验
        max_text_len = data.get('max_text_length')
        try:
            max_text_len = int(max_text_len) if max_text_len is not None else None
        except Exception:
            max_text_len = None
        if max_text_len is not None and max_text_len > 0 and len(text) > max_text_len:
            return jsonify({
                'code': 1,
                'msg': f'文本过长（{len(text)}字），单次最多支持 {max_text_len} 字，请分段生成',
                'data': None
            }), 400

        # 整体耗时上限：默认 600s，可通过 max_total_seconds 调整；<=0 表示不限制
        max_total_seconds_raw = data.get('max_total_seconds')
        try:
            max_total_seconds = int(max_total_seconds_raw) if max_total_seconds_raw is not None else 600
        except Exception:
            max_total_seconds = 600
        start_ts = time.time()

        if voice_clone_engine is None:
            return jsonify({'code': 1, 'msg': 'Voice Clone 引擎未初始化', 'data': None}), 500

        # 获取全局 TTS 引擎
        try:
            gs = get_global_state()
            tts_engine = gs.get_tts_engine()
        except Exception as e:
            logger.error(f'获取TTS引擎失败: {e}', exc_info=True)
            return jsonify({'code': 1, 'msg': 'TTS引擎不可用，请检查配置', 'data': None}), 500

        tts_engine_name = (data.get('tts_engine') or '').strip() or 'pyttsx3'
        # 优先使用前端显式传入的 tts_voice，其次使用 voice_id，最后兜底为通用中文 "zh"
        tts_voice = data.get('tts_voice') or data.get('voice_id') or 'zh'

        # 为 Voice Clone 路径选择一个对本地 pyttsx3 友好的基础音色
        # 注意：这里的音色只作为克隆前的“中性发音源”，不会影响最终目标音色
        def _choose_pyttsx3_voice(text_value: str, requested: str) -> str:
            req = (requested or '').strip().lower()
            txt = text_value or ''
            has_chinese = any('\u4e00' <= ch <= '\u9fff' for ch in txt)
            if has_chinese:
                # 文本包含中文时，优先使用本地中文女声，确保发音稳定
                return 'zh-CN-XiaoxiaoNeural'
            # 非中文文本，根据请求大致区分中英文
            if req.startswith('en') or 'english' in req:
                return 'en-US-JennyNeural'
            return 'zh-CN-XiaoxiaoNeural'

        base_voice = _choose_pyttsx3_voice(text, tts_voice)

        # 为确保完全离线，Voice Clone 路径强制使用本地 pyttsx3 引擎
        if tts_engine_name.lower() != 'pyttsx3':
            logger.warning(f"VoiceClone 请求引擎 {tts_engine_name} 非 pyttsx3，已强制改为 pyttsx3")
            tts_engine_name = 'pyttsx3'

        out_dir = OUTPUTS_DIR / 'voice_clone_tts'
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        tts_path = out_dir / f'tts_{ts}.mp3'
        clone_path = out_dir / f'clone_{ts}.wav'

        logger.info(
            f'🎙️ VoiceClone TTS: text_len={len(text)}, engine={tts_engine_name}, '
            f'requested_voice={tts_voice}, base_voice={base_voice}'
        )

        # 主路径：使用本地 pyttsx3 + 安全基础音色
        tts_ok = tts_engine.synthesize(text, str(tts_path), engine='pyttsx3', voice=base_voice)

        # 如果TTS失败或生成的文件无效（检查最小1KB大小），尝试本地 pyttsx3 备用音色
        MIN_VALID_SIZE = 1024
        def is_valid_audio(path):
            """检查音频文件是否有效"""
            return path.exists() and path.stat().st_size >= MIN_VALID_SIZE
        
        if not tts_ok or not is_valid_audio(tts_path):
            logger.warning(f'⚠️ 主TTS引擎失败（文件无效或过小），尝试本地备用音色...')
            # 清理损坏的文件
            if tts_path.exists() and tts_path.stat().st_size < MIN_VALID_SIZE:
                try:
                    tts_path.unlink()
                    logger.info(f'已清理损坏的TTS文件')
                except:
                    pass
            
            # 完全离线：仅在本地 pyttsx3 内部轮换音色，不再使用 Edge-TTS / gTTS
            fallback_voices = []
            # 优先尝试通用中文/英文本地音色
            if base_voice != 'zh-CN-XiaoxiaoNeural':
                fallback_voices.append('zh-CN-XiaoxiaoNeural')
            fallback_voices.extend(['zh-CN', 'en-US'])

            for fv in fallback_voices:
                try:
                    logger.info(f'🎙️ VoiceClone TTS: 尝试本地备用 pyttsx3 音色 {fv}')
                    tts_ok = tts_engine.synthesize(text, str(tts_path), engine='pyttsx3', voice=fv)
                    if tts_ok and is_valid_audio(tts_path):
                        logger.info(f'✅ 本地备用音色 {fv} 合成成功')
                        break
                except Exception as e:
                    logger.error(f'❗ 本地备用 pyttsx3 音色 {fv} 失败: {e}', exc_info=True)
                    tts_ok = False

        if not tts_ok or not is_valid_audio(tts_path):
            return jsonify({
                'code': 1,
                'msg': 'TTS 合成失败：本地语音引擎在当前系统不可用，请检查 Windows 语音服务或语音包安装情况',
                'data': None
            }), 500

        elapsed = time.time() - start_ts
        if max_total_seconds > 0 and elapsed > max_total_seconds:
            logger.error(f'⏰ VoiceClone TTS 流水线超时（TTS阶段耗时 {elapsed:.1f}s，限制 {max_total_seconds}s）')
            return jsonify({
                'code': 1,
                'msg': '生成超时：TTS 合成耗时过长，请缩短文本长度或稍后重试',
                'data': None
            }), 504

        reference_audio = data.get('reference_audio') or data.get('reference_voice')
        target_voice = data.get('target_voice') or data.get('voice_id') or 'zh'

        # 使用自定义参考音频优先，否则使用内置音色
        if reference_audio:
            logger.info(f'🎧 使用自定义参考音色克隆: ref={reference_audio}')
            output_path = voice_clone_engine.clone_with_custom_voice(
                source_audio=str(tts_path),
                reference_voice=reference_audio,
                output_path=str(clone_path)
            )
        else:
            logger.info(f'🎧 使用内置音色克隆: target={target_voice}')
            output_path = voice_clone_engine.clone_voice(
                source_audio=str(tts_path),
                target_voice=target_voice,
                output_path=str(clone_path)
            )

        # 校验 Voice Clone 输出；若文件不存在或为空，则回退到基础 TTS 音频
        try:
            p = Path(output_path).resolve() if output_path else None
        except Exception:
            p = None

        if (not p) or (not p.exists()) or p.stat().st_size <= 0:
            logger.warning('⚠️ Voice Clone 输出无效，将回退到基础 TTS 音频')
            p = Path(tts_path).resolve()

        elapsed = time.time() - start_ts
        if max_total_seconds > 0 and elapsed > max_total_seconds:
            logger.error(f'⏰ VoiceClone TTS 流水线超时（总耗时 {elapsed:.1f}s，限制 {max_total_seconds}s）')
            return jsonify({
                'code': 1,
                'msg': '生成超时：Voice Clone 推理耗时过长，请稍后重试或减少文本长度',
                'data': None
            }), 504

        try:
            rel = p.relative_to(PROJECT_ROOT)
            rel_str = str(rel).replace('\\', '/')
        except Exception:
            rel_str = f'temp/outputs/{p.name}'

        audio_url = '/' + rel_str.lstrip('/')

        return jsonify({
            'code': 0,
            'msg': '生成成功',
            'data': {
                'audio_path': rel_str,
                'audio_url': audio_url
            }
        })

    except Exception as e:
        logger.error(f'❌ 文本克隆配音失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'生成失败: {str(e)}', 'data': None}), 500
