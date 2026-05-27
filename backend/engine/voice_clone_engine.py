# -*- coding: utf-8 -*-
"""
Voice Clone Engine
语音克隆引擎 - 完整实现
基于本地部署的voice_clone模型
"""

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class VoiceCloneEngine:
    """语音克隆引擎 - 完整实现"""
    
    def __init__(self, voice_clone_path: Optional[str] = None,
                 model_path: Optional[str] = None):
        """
        初始化语音克隆引擎
        优先级：显式参数 > 环境变量 > ai_config.json > 系统PATH/默认

        环境变量：
        - VOICE_CLONE_EXE: voice_clone 可执行文件路径或命令名
        - VOICE_CLONE_MODEL_DIR: OpenVoice 模型目录
        """
        # 读取配置（可选）
        cfg_exe = ''
        cfg_model = ''
        try:
            from backend.config.ai_config import get_config_manager
            cm = get_config_manager()
            cfg_exe = getattr(cm.tts_model_config, 'voice_clone_executable_path', '') or ''
            cfg_model = getattr(cm.tts_model_config, 'voice_clone_model_path', '') or ''
        except Exception:
            pass

        # 合并优先级
        env_exe = os.getenv('VOICE_CLONE_EXE') or ''
        env_model = os.getenv('VOICE_CLONE_MODEL_DIR') or ''
        exe = (voice_clone_path or env_exe or cfg_exe or 'voice_clone')
        model_dir = (model_path or env_model or cfg_model or '')

        # 解析可执行文件：如果是命令名则用 which 定位
        resolved_exe = exe
        if not Path(exe).exists():
            which = shutil.which(exe)
            if which:
                resolved_exe = which

        self.voice_clone_path = resolved_exe
        self.model_path = model_dir

        if not Path(self.voice_clone_path).exists() and not shutil.which(self.voice_clone_path):
            logger.warning('⚠️  voice_clone 未找到: %s（可设置环境变量 VOICE_CLONE_EXE 或在 ai_config.json 的 tts_model.voice_clone_executable_path 中配置）' % self.voice_clone_path)
        else:
            logger.info('✅ 语音克隆引擎初始化完成，使用: %s' % self.voice_clone_path)

        if self.model_path and not Path(self.model_path).exists():
            logger.warning('⚠️  模型路径不存在: %s（可设置环境变量 VOICE_CLONE_MODEL_DIR 或在 ai_config.json 的 tts_model.voice_clone_model_path 中配置）' % self.model_path)

        # 内置音色列表
        self.builtin_voices = [
            'en-au', 'en-br', 'en-default', 'en-india', 
            'en-newest', 'en-us', 'es', 'fr', 'jp', 'kr', 'zh'
        ]

    def get_status(self) -> Dict[str, Any]:
        """返回当前语音克隆引擎的健康状态

        Returns:
            dict: {
                'ready': bool,            # 是否满足运行的基本条件
                'executable_path': str,   # 当前使用的可执行文件路径/命令
                'model_path': str,        # 模型目录
                'executable_ok': bool,    # 可执行是否存在或在 PATH 中
                'model_ok': bool          # 模型目录是否存在
            }
        """
        exe_path = self.voice_clone_path
        model_path = self.model_path or ''

        exe_ok = False
        try:
            if exe_path:
                if Path(exe_path).exists() or shutil.which(exe_path):
                    exe_ok = True
        except Exception:
            exe_ok = False

        model_ok = False
        try:
            if model_path:
                model_ok = Path(model_path).exists()
        except Exception:
            model_ok = False

        ready = bool(exe_ok and model_ok)

        return {
            'ready': ready,
            'executable_path': exe_path,
            'model_path': model_path,
            'executable_ok': exe_ok,
            'model_ok': model_ok,
        }
    
    def clone_voice(self, source_audio: str, target_voice: str, 
                   output_path: str = None, save_tone: bool = False) -> str:
        """
        克隆语音
        
        Args:
            source_audio: 源音频文件路径
            target_voice: 目标音色（可以是内置音色名或音频文件路径）
            output_path: 输出路径（可选）
            save_tone: 是否保存音色特征
            
        Returns:
            输出音频文件路径
        """
        try:
            logger.info(f'🎙️ 开始语音克隆: {source_audio} -> {target_voice}')

            exe_path = Path(self.voice_clone_path)
            work_dir = None
            try:
                if exe_path.exists():
                    work_dir = exe_path.parent.resolve()
            except Exception:
                work_dir = None

            if not work_dir:
                logger.error(f'❗ voice_clone 可执行文件不存在或不可用: {self.voice_clone_path}')
                return None

            src_abs = Path(source_audio)
            try:
                src_abs = src_abs.resolve()
            except Exception:
                pass
            if not src_abs.exists():
                logger.error(f'❗ 源音频文件不存在: {source_audio}')
                return None

            ts = int(time.time() * 1000)
            src_suffix = src_abs.suffix or '.wav'
            src_rel_name = f'src_{ts}{src_suffix}'
            src_in_dir = work_dir / src_rel_name

            try:
                shutil.copy2(src_abs, src_in_dir)
            except Exception as e:
                logger.error(f'❗ 复制源音频到 voice_clone 工作目录失败: {e}')
                return None

            target_arg = target_voice
            if target_voice not in self.builtin_voices:
                tv_path = Path(target_voice)
                tv_abs = tv_path
                try:
                    tv_abs = tv_path.resolve()
                except Exception:
                    pass
                if tv_abs.exists():
                    ref_suffix = tv_abs.suffix or '.wav'
                    ref_rel_name = f'ref_{ts}{ref_suffix}'
                    ref_in_dir = work_dir / ref_rel_name
                    try:
                        shutil.copy2(tv_abs, ref_in_dir)
                        target_arg = str(ref_rel_name)
                    except Exception as e:
                        logger.error(f'❗ 复制参考音色到 voice_clone 工作目录失败: {e}')
                        return None

            # 构建命令
            cmd = [
                str(exe_path),
                '-s', str(src_rel_name),
                '-t', str(target_arg),
                '-m', self.model_path
            ]

            # 添加输出路径
            if output_path:
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                cmd.extend(['-o', str(output_dir)])
                
                # 指定输出文件名
                output_name = Path(output_path).name
                cmd.extend(['-n', output_name])
            
            # 是否保存音色特征
            if save_tone:
                cmd.append('-S')
            
            logger.info(f'执行命令: {" ".join(cmd)}')
            
            # 执行命令
            result = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=300,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                """尽量推断实际生成的输出文件路径，避免文件名被二次加扩展导致 404"""
                final_path: Optional[Path] = None

                if output_path:
                    exact = Path(output_path)
                    # 1) 首选：完全匹配我们传入的 output_path
                    if exact.exists():
                        final_path = exact
                    else:
                        # 2) voice_clone 可能会在我们传入的文件名上再追加扩展名
                        #    例如传入 clone_xxx.wav，实际生成 clone_xxx.wav.wav
                        parent = exact.parent
                        stem = exact.stem
                        if parent.exists():
                            for p in parent.glob(stem + '.*'):
                                if p.is_file():
                                    final_path = p
                                    break
                    if final_path is None:
                        # 兜底：仍然返回原始 output_path，至少日志中可见
                        final_path = exact
                else:
                    # 未显式指定 output_path 时，按约定的 "source--target" 规则推断
                    source_name = Path(source_audio).stem
                    target_name = target_voice if target_voice in self.builtin_voices else Path(target_voice).stem
                    parent = Path(source_audio).parent
                    default = parent / f"{source_name}--{target_name}.wav"

                    if default.exists():
                        final_path = default
                    else:
                        # 在目录中搜索前缀匹配的文件（任意扩展名）
                        pattern = f"{source_name}--{target_name}.*"
                        if parent.exists():
                            for p in parent.glob(pattern):
                                if p.is_file():
                                    final_path = p
                                    break
                        if final_path is None:
                            final_path = default

                # 确认实际生成的输出文件有效，否则视为失败
                try:
                    if (not final_path) or (not final_path.exists()) or final_path.stat().st_size <= 0:
                        stderr_preview = ''
                        stdout_preview = ''
                        try:
                            stderr_preview = (result.stderr or '')[:400]
                        except Exception:
                            stderr_preview = ''
                        try:
                            stdout_preview = (result.stdout or '')[:200]
                        except Exception:
                            stdout_preview = ''
                        logger.warning(
                            f'⚠️ 语音克隆进程返回成功，但未找到有效输出文件: '
                            f'stdout={stdout_preview!r}, stderr={stderr_preview!r}'
                        )
                        return None
                except Exception:
                    logger.warning('⚠️ 语音克隆进程返回成功，但检查输出文件时出错')
                    return None

                final_output = str(final_path)
                logger.info(f'✅ 语音克隆成功: {final_output}')
                return final_output
            else:
                logger.error(f'❗ 语音克隆失败: {result.stderr}')
                return None
                
        except Exception as e:
            logger.error(f'❗ 语音克隆异常: {e}', exc_info=True)
            return None
    
    def batch_clone_voice(self, source_audios: List[str], target_voice: str,
                         output_dir: str = None, save_tone: bool = False) -> List[str]:
        """
        批量克隆语音
        
        Args:
            source_audios: 源音频文件路径列表
            target_voice: 目标音色
            output_dir: 输出目录
            save_tone: 是否保存音色特征
            
        Returns:
            输出音频文件路径列表
        """
        try:
            logger.info(f'🎙️ 批量语音克隆: {len(source_audios)}个文件')
            
            # 构建源文件列表（用冒号分隔）
            source_list = ':'.join(source_audios)
            
            # 构建命令
            cmd = [
                self.voice_clone_path,
                '-s', source_list,
                '-t', target_voice,
                '-m', self.model_path
            ]
            
            # 添加输出目录
            if output_dir:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                cmd.extend(['-o', output_dir])
            
            # 是否保存音色特征
            if save_tone:
                cmd.append('-S')
            
            logger.info(f'执行批量克隆命令')
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                # 生成输出文件路径列表
                output_paths = []
                target_name = target_voice if target_voice in self.builtin_voices else Path(target_voice).stem
                
                for source_audio in source_audios:
                    source_name = Path(source_audio).stem
                    output_file = f"{source_name}--{target_name}.wav"
                    
                    if output_dir:
                        output_file = str(Path(output_dir) / output_file)
                    
                    output_paths.append(output_file)
                
                logger.info(f'✅ 批量语音克隆成功: {len(output_paths)}个文件')
                return output_paths
            else:
                logger.error(f'❗ 批量语音克隆失败: {result.stderr}')
                return []
                
        except Exception as e:
            logger.error(f'❗ 批量语音克隆异常: {e}', exc_info=True)
            return []
    
    def clone_with_custom_voice(self, source_audio: str, reference_voice: str,
                               output_path: str = None) -> str:
        """
        使用自定义音色克隆
        
        Args:
            source_audio: 源音频文件
            reference_voice: 参考音色文件
            output_path: 输出路径
            
        Returns:
            输出音频文件路径
        """
        return self.clone_voice(source_audio, reference_voice, output_path, save_tone=True)
    
    def get_builtin_voices(self) -> List[Dict]:
        """
        获取内置音色列表
        
        Returns:
            音色列表
        """
        voices = []
        
        voice_info = {
            'en-au': {'name': '英语-澳大利亚', 'language': 'English', 'region': 'Australia'},
            'en-br': {'name': '英语-英国', 'language': 'English', 'region': 'Britain'},
            'en-default': {'name': '英语-默认', 'language': 'English', 'region': 'Default'},
            'en-india': {'name': '英语-印度', 'language': 'English', 'region': 'India'},
            'en-newest': {'name': '英语-最新', 'language': 'English', 'region': 'Newest'},
            'en-us': {'name': '英语-美国', 'language': 'English', 'region': 'US'},
            'es': {'name': '西班牙语', 'language': 'Spanish', 'region': 'Spain'},
            'fr': {'name': '法语', 'language': 'French', 'region': 'France'},
            'jp': {'name': '日语', 'language': 'Japanese', 'region': 'Japan'},
            'kr': {'name': '韩语', 'language': 'Korean', 'region': 'Korea'},
            'zh': {'name': '中文', 'language': 'Chinese', 'region': 'China'}
        }
        
        for voice_id in self.builtin_voices:
            info = voice_info.get(voice_id, {})
            voices.append({
                'id': voice_id,
                'name': info.get('name', voice_id),
                'language': info.get('language', 'Unknown'),
                'region': info.get('region', 'Unknown'),
                'type': 'builtin'
            })
        
        return voices
    
    def extract_tone(self, audio_path: str) -> str:
        """
        提取音色特征
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            音色特征文件路径
        """
        try:
            logger.info(f'🎵 提取音色特征: {audio_path}')
            
            # 使用任意目标音色执行一次克隆，并保存音色特征
            cmd = [
                self.voice_clone_path,
                '-s', audio_path,
                '-t', 'zh',  # 使用任意内置音色
                '-m', self.model_path,
                '-S'  # 保存音色特征
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                # 音色特征文件路径
                tone_file = Path(audio_path).with_suffix('.tone')
                
                if tone_file.exists():
                    logger.info(f'✅ 音色特征提取成功: {tone_file}')
                    return str(tone_file)
                else:
                    logger.warning('⚠️  音色特征文件未生成')
                    return None
            else:
                logger.error(f'❗ 提取音色特征失败: {result.stderr}')
                return None
                
        except Exception as e:
            logger.error(f'❗ 提取音色特征异常: {e}', exc_info=True)
            return None
