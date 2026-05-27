# -*- coding: utf-8 -*-
"""
Voiceover Service
AI配音服务 - 完整实现
多种AI音色、文字转语音生成、语速语调调整
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from backend.config.paths import PROJECT_ROOT
from backend.engine.audio_processor import AudioProcessor

logger = logging.getLogger(__name__)


class VoiceoverService:
    """AI配音服务 - 完整实现"""
    
    def __init__(self, db_manager, socketio, tts_engine):
        """
        初始化AI配音服务
        
        Args:
            db_manager: 数据库管理器
            socketio: SocketIO实例
            tts_engine: TTS引擎
        """
        self.db_manager = db_manager
        self.socketio = socketio
        self.tts_engine = tts_engine
        # 独立的音频处理引擎，用于后处理配音音频
        self.audio_processor = AudioProcessor()
        
        # 可用的AI音色列表
        self.available_voices = self._init_voices()
        
        logger.info(f'✅ AI配音服务初始化完成，可用音色: {len(self.available_voices)}个')
    
    def _init_voices(self) -> List[Dict]:
        """初始化可用音色列表"""
        return [
            {
                'id': 'zh-CN-XiaoxiaoNeural',
                'name': '晓晓',
                'gender': 'female',
                'language': 'zh-CN',
                'description': '温柔女声，适合解说',
                'style': ['gentle', 'friendly']
            },
            {
                'id': 'zh-CN-YunxiNeural',
                'name': '云希',
                'gender': 'male',
                'language': 'zh-CN',
                'description': '成熟男声，适合纪录片',
                'style': ['serious', 'calm']
            },
            {
                'id': 'zh-CN-YunyangNeural',
                'name': '云扬',
                'gender': 'male',
                'language': 'zh-CN',
                'description': '年轻男声，适合活力内容',
                'style': ['energetic', 'cheerful']
            },
            {
                'id': 'zh-CN-XiaoyiNeural',
                'name': '晓伊',
                'gender': 'female',
                'language': 'zh-CN',
                'description': '甜美女声，适合轻松内容',
                'style': ['sweet', 'cute']
            },
            {
                'id': 'zh-CN-YunjianNeural',
                'name': '云健',
                'gender': 'male',
                'language': 'zh-CN',
                'description': '浑厚男声，适合严肃内容',
                'style': ['deep', 'authoritative']
            }
        ]

    def _normalize_voice_id(self, voice_id: str) -> str:
        vid = (voice_id or 'zh-CN-XiaoxiaoNeural').strip()
        lower = vid.lower()
        if 'neural' in lower and '-' in lower:
            return vid
        alias = {
            'zh': 'zh-CN-XiaoxiaoNeural',
            'zh-cn': 'zh-CN-XiaoxiaoNeural',
            'en-us': 'en-US-JennyNeural',
            'en-default': 'en-US-JennyNeural',
            'en-newest': 'en-US-JennyNeural',
            'en-au': 'en-AU-NatashaNeural',
            'en-br': 'en-GB-LibbyNeural',
            'en-gb': 'en-GB-LibbyNeural',
            'en-india': 'en-IN-NeerjaNeural',
            'es': 'es-ES-ElviraNeural',
            'fr': 'fr-FR-DeniseNeural',
            'jp': 'ja-JP-NanamiNeural',
            'ja': 'ja-JP-NanamiNeural',
            'kr': 'ko-KR-SunHiNeural',
            'ko': 'ko-KR-SunHiNeural',
        }
        return alias.get(lower, vid)
    
    def get_available_voices(self, language: str = None, gender: str = None) -> List[Dict]:
        """
        获取可用音色列表
        
        Args:
            language: 语言筛选
            gender: 性别筛选
            
        Returns:
            音色列表
        """
        try:
            voices = self.available_voices
            
            if language:
                voices = [v for v in voices if v['language'] == language]
            
            if gender:
                voices = [v for v in voices if v['gender'] == gender]
            
            logger.info(f'✅ 获取音色列表: {len(voices)}个')
            
            return voices
            
        except Exception as e:
            logger.error(f'❗ 获取音色列表失败: {e}', exc_info=True)
            return []
    
    def create_voiceover_project(self, data: Dict) -> Dict:
        """
        创建AI配音项目
        
        Args:
            data: 项目数据
                - name: 项目名称
                - text: 配音文本
                - voice_id: 音色ID
                - rate: 语速
                - pitch: 音调
                
        Returns:
            项目信息
        """
        try:
            logger.info('🎙️ 创建AI配音项目...')
            
            # 创建项目
            project = self.db_manager.create_project(
                name=data.get('name', 'AI配音项目'),
                project_type='voiceover',
                description='AI配音项目',
                template='voiceover'
            )
            
            project_id = project['id']
            
            # 保存配置
            config = {
                'text': data.get('text', ''),
                'voice_id': data.get('voice_id', 'zh-CN-XiaoxiaoNeural'),
                'rate': data.get('rate', '+0%'),  # -50% to +100%
                'pitch': data.get('pitch', '+0Hz'),  # -50Hz to +50Hz
                'volume': data.get('volume', '+0%'),  # -100% to +100%
                'style': data.get('style', 'general')
            }
            
            self.db_manager.update_project(project_id, {'config': config})
            
            logger.info(f'✅ AI配音项目创建成功: {project_id}')
            
            return {
                'project_id': project_id,
                'project': project,
                'config': config
            }
            
        except Exception as e:
            logger.error(f'❗ 创建AI配音项目失败: {e}', exc_info=True)
            raise
    
    def generate_voiceover(self, text: str, voice_config: Dict) -> str:
        """
        生成AI配音
        
        Args:
            text: 配音文本
            voice_config: 配音配置
                - voice_id: 音色ID
                - rate: 语速
                - pitch: 音调
                - volume: 音量
                
        Returns:
            音频文件路径
        """
        try:
            logger.info(f'🎙️ 生成AI配音: {len(text)}字')

            # 读取基本配置
            voice_id_raw = voice_config.get('voice_id', 'zh-CN-XiaoxiaoNeural')
            voice_id = self._normalize_voice_id(voice_id_raw)
            rate = voice_config.get('rate', '+0%')
            volume = voice_config.get('volume', '+0%')
            pitch = voice_config.get('pitch', 0)

            # 前端传入的引擎类型（edge-tts/gtts/azure/voice-pro 等）
            raw_engine = (voice_config.get('engine') or '').lower()
            if raw_engine not in ('', 'pyttsx3', 'local', 'offline'):
                logger.warning(f'AI配音请求在线TTS引擎 {raw_engine}，当前版本已强制使用本地 pyttsx3 离线合成')
            preferred_engine = 'pyttsx3'
            
            # 读取高级配置参数（情感TTS、说话人嵌入、音频特征等）
            advanced_config = {
                # 情感TTS配置
                'emotion_type': voice_config.get('emotion_type', 'neutral'),
                'emotion_intensity': voice_config.get('emotion_intensity', 'moderate'),
                'emotion_modeling': voice_config.get('emotion_modeling', 'embedding'),
                'emotion_transfer': voice_config.get('emotion_transfer', 'moderate'),
                
                # 说话人嵌入配置
                'speaker_embedding_model': voice_config.get('speaker_embedding_model', 'ecapa-tdnn'),
                'embedding_dim': voice_config.get('embedding_dim', 256),
                'similarity_metric': voice_config.get('similarity_metric', 'cosine'),
                'embedding_fusion': voice_config.get('embedding_fusion', 'concat'),
                
                # 音频特征提取配置
                'audio_feature_type': voice_config.get('audio_feature_type', 'mel-spectrogram'),
                'mel_bins': voice_config.get('mel_bins', 80),
                'fft_size': voice_config.get('fft_size', 1024),
                'hop_length': voice_config.get('hop_length', 256),
                
                # 数据增强配置
                'time_stretch': voice_config.get('time_stretch', 'moderate'),
                'pitch_shift': voice_config.get('pitch_shift', 'semitone-2'),
                'noise_level': voice_config.get('noise_level', 'light'),
                'volume_variation': voice_config.get('volume_variation', 'small'),
                
                # 技术性能优化
                'inference_mode': voice_config.get('inference_mode', 'balanced'),
                'compute_device': voice_config.get('compute_device', 'auto'),
                'batch_size': voice_config.get('batch_size', 8),
                'cache_strategy': voice_config.get('cache_strategy', 'smart')
            }
            
            logger.info(f'📋 配音配置: engine={preferred_engine}, voice={voice_id}, rate={rate}, volume={volume}, emotion={advanced_config["emotion_type"]}')

            # 生成输出路径（统一到 PROJECT_ROOT/output/audios）
            output_dir = PROJECT_ROOT / 'output' / 'audios'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"voiceover_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"

            # 构造尝试顺序：优先用户选择，本地引擎pyttsx3作为可靠备用
            # 注意：由于网络限制，pyttsx3的优先级提高，确保至少有一个可用引擎
            engine_candidates = ['pyttsx3']

            success = False

            for eng in engine_candidates:
                if eng not in self.tts_engine.available_engines:
                    logger.warning(f'TTS引擎 {eng} 未在当前环境中可用，跳过')
                    continue

                try:
                    if eng == 'gtts':
                        # 推断 gTTS 语言（简单从 voice_id/配置推断）
                        lang = 'zh-CN'
                        try:
                            if isinstance(voice_id, str) and '-' in voice_id:
                                prefix = voice_id.split('-', 1)[0].lower()
                                if prefix in ('zh', 'zhcn', 'zh-cn'):
                                    lang = 'zh-CN'
                                elif prefix in ('en', 'enus', 'en-us'):
                                    lang = 'en'
                                elif prefix in ('ja', 'ja-jp'):
                                    lang = 'ja'
                                elif prefix in ('ko', 'ko-kr'):
                                    lang = 'ko'
                        except Exception:
                            pass

                        success = self.tts_engine.synthesize(
                            text=text,
                            output_path=str(output_path),
                            engine='gtts',
                            lang=lang,
                            slow=False,
                            advanced_config=advanced_config
                        )
                        if success:
                            logger.info(f'✅ gTTS 合成成功: {output_path}')

                    elif eng == 'pyttsx3':
                        success = self.tts_engine.synthesize(
                            text=text,
                            output_path=str(output_path),
                            engine='pyttsx3',
                            voice=voice_id,
                            rate=rate,
                            volume=volume,
                            advanced_config=advanced_config
                        )
                        if success:
                            logger.info(f'✅ pyttsx3 合成成功: {output_path}')

                    else:
                        # edge-tts、azure 或 voice-pro，都使用 voice/rate/volume 并传递高级配置
                        success = self.tts_engine.synthesize(
                            text=text,
                            output_path=str(output_path),
                            engine=eng,
                            voice=voice_id,
                            rate=rate,
                            volume=volume,
                            pitch=pitch,
                            advanced_config=advanced_config
                        )
                        if success:
                            logger.info(f'✅ {eng} 合成成功: {output_path}')

                except Exception as e:
                    logger.error(f'❗ 使用引擎 {eng} 合成失败: {e}', exc_info=True)
                    success = False

                if success:
                    break

            if success:
                logger.info(f'✅ AI配音生成成功: {output_path}')
                return str(output_path)
            else:
                fallback_voice = self._normalize_voice_id('zh-CN-XiaoxiaoNeural')
                try:
                    logger.warning('所有首选TTS引擎失败，尝试本地兜底音色')
                    ok = self.tts_engine.synthesize(
                        text=text,
                        output_path=str(output_path),
                        engine='pyttsx3',
                        voice=fallback_voice,
                        rate=rate,
                        volume=volume,
                        advanced_config=advanced_config
                    )
                except Exception as e:
                    logger.error(f'本地兜底音色合成失败: {e}', exc_info=True)
                    ok = False
                if ok and output_path.exists():
                    logger.info(f'✅ 本地兜底音色合成成功: {output_path}')
                    return str(output_path)
                raise Exception('TTS引擎生成失败')
            
        except Exception as e:
            logger.error(f'❗ 生成AI配音失败: {e}', exc_info=True)
            raise
    
    def batch_generate_voiceovers(self, texts: List[str], voice_config: Dict) -> List[str]:
        """
        批量生成AI配音
        
        Args:
            texts: 文本列表
            voice_config: 配音配置
            
        Returns:
            音频文件路径列表
        """
        try:
            logger.info(f'🎙️ 批量生成AI配音: {len(texts)}段')
            
            output_paths = []
            
            for i, text in enumerate(texts):
                try:
                    output_path = self.generate_voiceover(text, voice_config)
                    output_paths.append(output_path)
                    
                    # 发送进度更新
                    progress = (i + 1) / len(texts) * 100
                    self.socketio.emit('voiceover_progress', {
                        'progress': progress,
                        'current': i + 1,
                        'total': len(texts)
                    })
                    
                except Exception as e:
                    logger.error(f'❗ 生成第{i+1}段配音失败: {e}')
                    output_paths.append(None)
            
            success_count = len([p for p in output_paths if p])
            logger.info(f'✅ 批量配音完成: {success_count}/{len(texts)}')
            
            return output_paths
            
        except Exception as e:
            logger.error(f'❗ 批量生成配音失败: {e}', exc_info=True)
            raise
    
    def adjust_voice_parameters(self, audio_path: str, adjustments: Dict) -> str:
        """
        调整语音参数
        
        Args:
            audio_path: 原始音频路径
            adjustments: 调整参数
                - speed: 速度调整（0.5-2.0）
                - pitch: 音调调整（-12 to +12 半音）
                - volume: 音量调整（0.0-2.0）
                
        Returns:
            调整后的音频路径
        """
        try:
            logger.info(f'🔧 调整语音参数: {audio_path}')

            if not audio_path:
                raise ValueError('audio_path 不能为空')

            # 提取调整参数并限制范围
            try:
                speed = float(adjustments.get('speed', 1.0) or 1.0)
            except Exception:
                speed = 1.0
            speed = max(0.5, min(2.0, speed))

            try:
                pitch = float(adjustments.get('pitch', 0.0) or 0.0)
            except Exception:
                pitch = 0.0
            pitch = max(-12.0, min(12.0, pitch))  # 以半音为单位

            try:
                volume = float(adjustments.get('volume', 1.0) or 1.0)
            except Exception:
                volume = 1.0
            volume = max(0.0, min(2.0, volume))

            # 如果没有任何变化，直接返回原路径
            if abs(speed - 1.0) < 1e-3 and abs(pitch) < 1e-3 and abs(volume - 1.0) < 1e-3:
                logger.info('ℹ️ 未检测到参数变化，返回原始音频')
                return audio_path

            input_path = Path(audio_path)
            if not input_path.is_absolute():
                input_path = PROJECT_ROOT / audio_path
            if not input_path.exists():
                raise FileNotFoundError(f'音频文件不存在: {input_path}')

            output_dir = PROJECT_ROOT / 'output' / 'audios'
            output_dir.mkdir(parents=True, exist_ok=True)
            ext = input_path.suffix or '.mp3'
            output_path = output_dir / f"{input_path.stem}_adjusted_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"

            # 构建音频滤镜：优先考虑音量和语速，音高通过 asetrate 粗略调整
            filters = []

            if abs(pitch) > 1e-3:
                # 简单基于半音的移调：每个半音倍率为 2^(n/12)
                semitone_ratio = 2 ** (pitch / 12.0)
                # 固定采样率为 44100Hz，先改变采样率再重采样回 44100
                filters.append(f'asetrate=44100*{semitone_ratio:.5f}')
                filters.append('aresample=44100')

            if abs(speed - 1.0) > 1e-3:
                # atempo 只支持 0.5-2.0，前面已经做过裁剪
                filters.append(f'atempo={speed:.3f}')

            # 音量调整
            filters.append(f'volume={volume:.3f}')

            filter_str = ','.join(filters)

            cmd = [
                'ffmpeg',
                '-y',
                '-i', str(input_path),
                '-filter:a', filter_str,
                str(output_path)
            ]

            logger.info(f'🎛️ FFmpeg 音频参数调整命令: {" ".join(cmd)}')
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                logger.error(f'❗ 音频参数调整失败: {result.stderr}')
                raise RuntimeError(f'音频参数调整失败: {result.stderr[:200]}')

            logger.info(f'✅ 参数调整完成: {output_path}')

            return str(output_path)

        except Exception as e:
            logger.error(f'❗ 调整参数失败: {e}', exc_info=True)
            raise
    
    def merge_voiceovers(self, audio_paths: List[str], output_path: str = None) -> str:
        """
        合并多段配音
        
        Args:
            audio_paths: 音频文件路径列表
            output_path: 输出路径
            
        Returns:
            合并后的音频路径
        """
        try:
            logger.info(f'🔗 合并配音: {len(audio_paths)}段')

            if not audio_paths:
                raise ValueError('audio_paths 不能为空')

            # 过滤无效路径
            valid_paths = [str(p) for p in audio_paths if p]
            if not valid_paths:
                raise ValueError('没有可用的音频路径用于合并')

            if not output_path:
                output_dir = PROJECT_ROOT / 'output' / 'audios'
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = str(output_dir / f"merged_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3")

            # 使用 AudioProcessor 进行实际合并
            ok = self.audio_processor.merge_audios(valid_paths, output_path)
            if not ok:
                raise RuntimeError('音频合并失败')

            logger.info(f'✅ 配音合并完成: {output_path}')

            return output_path

        except Exception as e:
            logger.error(f'❗ 合并配音失败: {e}', exc_info=True)
            raise
    
    def preview_voice(self, voice_id: str, sample_text: str = None, engine: Optional[str] = None) -> str:
        """预览音色

        Args:
            voice_id: 音色ID
            sample_text: 示例文本
            engine: 前端可选指定的TTS引擎标识（edge-tts / azure / gtts / pyttsx3 等）

        Returns:
            预览音频路径
        """
        try:
            logger.info(f'👂 预览音色: {voice_id}, engine={engine}')
            # 自动清理过期的预览缓存，避免长时间占用磁盘
            try:
                self.cleanup_preview_cache(max_age_hours=24)
            except Exception as cleanup_err:
                logger.warning(f'预览缓存清理失败（忽略，不影响本次生成）: {cleanup_err}')

            if not sample_text:
                sample_text = "大家好，这是音色预览示例。"

            output_dir = PROJECT_ROOT / 'output' / 'previews'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"preview_{voice_id}.mp3"

            # 规范化引擎标识，并根据前端偏好确定尝试顺序
            engine_norm = (engine or '').strip().lower()
            if engine_norm in ('azure', 'azure-tts'):
                preferred = 'azure'
            elif engine_norm in ('gtts', 'google', 'google-tts'):
                preferred = 'gtts'
            elif engine_norm in ('pyttsx3', 'local', 'offline'):
                preferred = 'pyttsx3'
            elif engine_norm in ('voice-pro', 'voice_pro', 'voicepro'):
                preferred = 'voice-pro'
            else:
                preferred = 'edge-tts'

            # 为了确保完全离线预览，如果请求的是在线引擎，则强制切换为 pyttsx3
            if preferred != 'pyttsx3':
                logger.warning(f'AI配音预览请求在线TTS引擎 {preferred}，当前版本已强制使用本地 pyttsx3 离线合成')
                preferred = 'pyttsx3'

            engine_candidates: List[str]
            engine_candidates = ['pyttsx3']

            ok = False

            for eng in engine_candidates:
                if eng not in self.tts_engine.available_engines:
                    logger.warning(f'TTS 预览引擎 {eng} 当前不可用，跳过')
                    continue

                try:
                    if eng == 'gtts':
                        # gTTS 仅支持按语言切换，无法细化到具体音色
                        lang = 'zh-CN'
                        try:
                            if isinstance(voice_id, str) and '-' in voice_id:
                                prefix = voice_id.split('-', 1)[0].lower()
                                if prefix in ('en', 'enus', 'en-us'):
                                    lang = 'en'
                                elif prefix in ('ja', 'ja-jp'):
                                    lang = 'ja'
                                elif prefix in ('ko', 'ko-kr'):
                                    lang = 'ko'
                        except Exception:
                            pass

                        ok = self.tts_engine.synthesize(
                            text=sample_text,
                            output_path=str(output_path),
                            engine='gtts',
                            lang=lang,
                            slow=False
                        )
                    else:
                        # edge-tts / azure / voice-pro / pyttsx3 等：始终携带 voice_id，尽量保持不同音色差异
                        ok = self.tts_engine.synthesize(
                            text=sample_text,
                            output_path=str(output_path),
                            engine=eng,
                            voice=voice_id,
                            rate='+0%',
                            volume='+0%',
                            pitch=0
                        )
                except Exception as synth_err:
                    logger.error(f'❗ 使用预览引擎 {eng} 合成失败: {synth_err}', exc_info=True)
                    ok = False

                if ok:
                    break

            if not ok:
                raise Exception('TTS 预览生成失败')

            logger.info(f'✅ 音色预览生成: {output_path}')

            return str(output_path)

        except Exception as e:
            logger.error(f'❗ 预览音色失败: {e}', exc_info=True)
            raise

    def cleanup_preview_cache(self, max_age_hours: int = 24) -> int:
        """清理过期的预览音频缓存文件

        Args:
            max_age_hours: 保留的最长小时数，早于该时间的预览文件会被删除

        Returns:
            实际删除的文件个数
        """
        try:
            preview_dir = PROJECT_ROOT / 'output' / 'previews'
            if not preview_dir.exists():
                return 0

            cutoff_ts = datetime.now().timestamp() - max_age_hours * 3600
            deleted = 0

            for f in preview_dir.glob('preview_*.mp3'):
                try:
                    stat = f.stat()
                    if stat.st_mtime < cutoff_ts:
                        f.unlink()
                        deleted += 1
                except Exception as fe:
                    logger.warning(f'❗ 删除预览缓存文件失败: {f}: {fe}')

            if deleted:
                logger.info(f'🧹 预览缓存清理完成，删除 {deleted} 个过期文件')
            return deleted
        except Exception as e:
            logger.error(f'❗ 预览缓存清理过程异常: {e}', exc_info=True)
            return 0
