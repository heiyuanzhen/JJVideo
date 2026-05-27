"""
原创解说剪辑服务 - 完整AI流程实现
视频画面分析 → 文案生成 → 智能配音 → 三同步
"""

import logging
import os
import json
import time
import uuid
import numpy as np
import hashlib
import cv2
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path

from backend.config.paths import PROJECT_ROOT, AUDIO_DIR, TEMP_DIR, OUTPUTS_DIR
from backend.engine import VideoProcessor
from backend.engine.video_composer import VideoComposer
from backend.engine.subtitle_generator import SubtitleGenerator

logger = logging.getLogger('AIJian')


class CommentaryServiceEnhanced:
    """原创解说剪辑服务 - 完整AI流程"""
    
    def __init__(self, db_manager, socketio, task_service):
        self.db_manager = db_manager
        self.socketio = socketio
        self.task_service = task_service
        
        # 初始化AI引擎
        self._init_ai_engines()
        
        logger.info('✅ 原创解说剪辑服务（增强版）初始化完成')
    
    def _init_ai_engines(self):
        """初始化所有AI引擎 - 使用全局状态管理器"""
        try:
            # 获取全局状态管理器
            from backend.core.global_state import get_global_state
            self.global_state = get_global_state()
            
            # 从全局状态获取引擎实例
            self.vision_analyzer = self.global_state.get_vision_analyzer()
            logger.info('✅ 视觉分析引擎加载成功（全局）')
        except Exception as e:
            logger.warning(f'⚠️ 视觉分析引擎加载失败: {e}')
            self.vision_analyzer = None
            self.global_state = None
        
        # 从全局状态获取所有引擎
        if self.global_state:
            self.script_generator = self.global_state.get_script_generator()
            self.sync_engine = self.global_state.get_sync_engine()
            self.tts_engine = self.global_state.get_tts_engine()
            self.multi_model = self.global_state.get_multi_model_manager()
            self.config_manager = self.global_state.config_manager
            logger.info('✅ 所有AI引擎从全局状态加载完成')
        else:
            self.script_generator = None
            self.sync_engine = None
            self.tts_engine = None
            self.multi_model = None
            self.config_manager = None

        # 初始化语音克隆引擎（用于本地克隆音色配音）
        try:
            from backend.engine.voice_clone_engine import VoiceCloneEngine
            vc_engine = VoiceCloneEngine()
            # 检查引擎是否真正可用
            status = vc_engine.get_status()
            if status.get('ready'):
                self.voice_clone_engine = vc_engine
                logger.info(f'✅ Voice Clone 引擎加载成功: exe={status.get("executable_path")}, model={status.get("model_path")}')
            else:
                self.voice_clone_engine = None
                logger.warning(
                    f'⚠️ Voice Clone 引擎未就绪：'
                    f'exe_ok={status.get("executable_ok")}, model_ok={status.get("model_ok")}, '
                    f'exe_path={status.get("executable_path")}, model_path={status.get("model_path")}'
                )
        except Exception as e:
            self.voice_clone_engine = None
            logger.error(f'❌ Voice Clone 引擎初始化失败: {e}', exc_info=True)
    
    def create_project(self, data: Dict) -> Dict:
        """创建原创解说项目"""
        try:
            logger.info('🎬 创建原创解说项目...')
            
            project = self.db_manager.create_project(
                name=data.get('name', '原创解说项目'),
                project_type='commentary',
                description='AI原创解说剪辑',
                template='commentary'
            )
            
            project_id = project['id']
            
            # 保存配置
            config = {
                'video_path': data.get('video_path', ''),
                'script': data.get('script', ''),
                'voice': data.get('voice', 'zh-CN-XiaoxiaoNeural'),
                # 默认使用本地 pyttsx3，避免在无网络环境下频繁触发云TTS失败
                'tts_engine': data.get('tts_engine') or data.get('ttsEngine') or 'pyttsx3',
                'auto_subtitle': data.get('auto_subtitle', True),
                'auto_bgm': data.get('auto_bgm', True),
                'style': data.get('style', 'professional'),
                # 字幕样式相关配置：允许前端覆盖默认大号样式和位置/字号
                'subtitle_style': data.get('subtitle_style') or data.get('subtitleStyle') or 'large',
                'subtitle_position': data.get('subtitle_position') or data.get('subtitlePosition') or 'bottom',
                'subtitle_font_size': data.get('subtitle_font_size') or data.get('subtitleFontSize') or None,
                # 高级字幕样式：字体 / 颜色 / 描边 / 背景
                'subtitle_font': data.get('subtitle_font') or data.get('subtitleFont') or None,
                'subtitle_color': data.get('subtitle_color') or data.get('subtitleColor') or None,
                'subtitle_bg_color': data.get('subtitle_bg_color') or data.get('subtitleBgColor') or None,
                'subtitle_stroke_color': data.get('subtitle_stroke_color') or data.get('subtitleStrokeColor') or None,
                'subtitle_stroke_width': data.get('subtitle_stroke_width') or data.get('subtitleStrokeWidth') or None,
            }
            
            # 保存音量控制配置
            voice_volume = data.get('voice_volume')
            bgm_volume = data.get('bgm_volume')
            original_audio_volume = data.get('original_audio_volume')
            if voice_volume is not None:
                config['voice_volume'] = float(voice_volume)
            if bgm_volume is not None:
                config['bgm_volume'] = float(bgm_volume)
            if original_audio_volume is not None:
                config['original_audio_volume'] = float(original_audio_volume)
            
            self.db_manager.update_project(project_id, {'config': config})
            
            logger.info(f'✅ 项目创建成功: {project_id}')
            
            return {
                'code': 0,
                'msg': '项目创建成功',
                'data': {
                    'project_id': project_id,
                    'project': project,
                    'config': config
                }
            }
            
        except Exception as e:
            logger.error(f'❌ 创建项目失败: {e}', exc_info=True)
            return {'code': 1, 'msg': f'创建失败: {str(e)}', 'data': None}
    
    def process_video(self, project_id: str, video_path: str, config: Dict) -> Dict:
        """
        完整处理流程：分析 → 生成 → 配音 → 同步
        """
        try:
            logger.info(f'🚀 开始处理项目: {project_id}')
            
            # 创建任务（写入数据库）
            task_id = str(uuid.uuid4())
            self.db_manager.create_task(
                task_id=task_id,
                task_type='commentary_process',
                project_id=project_id,
                input_data={'video_path': video_path, 'config': config}
            )
            # 标记运行中
            self.db_manager.update_task_status(task_id, 'running')
            
            # 发送进度
            self._emit_progress(task_id, 0, '开始处理...')
            
            # 步骤1: 视频分析 (0-30%)
            self._emit_progress(task_id, 5, '正在分析视频画面...')
            vision_results = self._analyze_video(video_path, task_id, config)
            
            if not vision_results:
                raise Exception('视频分析失败')
            
            self._emit_progress(task_id, 30, '视频分析完成')
            
            # 步骤2: AI生成文案 (30-50%)
            self._emit_progress(task_id, 35, '正在生成解说文案...')
            script = self._generate_script(vision_results, config, task_id)
            
            if not script:
                raise Exception('文案生成失败')
            
            self._emit_progress(task_id, 50, '文案生成完成')
            
            # 步骤3: 智能配音 (50-70%)
            self._emit_progress(task_id, 55, '正在生成配音...')
            audio_path = self._generate_voiceover(script, config, task_id)
            
            if not audio_path:
                raise Exception('配音生成失败')
            
            self._emit_progress(task_id, 70, '配音生成完成')
            
            # 步骤4: 三同步处理 (70-90%)
            self._emit_progress(task_id, 75, '正在执行三同步...')
            sync_results = self._sync_all(video_path, audio_path, script, vision_results, task_id)
            
            self._emit_progress(task_id, 90, '三同步完成')
            
            # 步骤5: 生成最终视频 (90-100%)
            self._emit_progress(task_id, 95, '正在生成最终视频...')
            output_path = self._compose_final_video(
                video_path, audio_path, script, sync_results, config, task_id
            )
            
            self._emit_progress(task_id, 100, '处理完成！')
            
            # 更新任务状态
            # 任务完成
            self.db_manager.update_task_progress(task_id, 100)
            self.db_manager.update_task_status(task_id, 'completed')
            
            # 保存结果
            result_data = {
                'vision_analysis': vision_results,
                'script': script,
                'audio_path': audio_path,
                'sync_results': sync_results,
                'output_path': output_path
            }
            # 将结果转换为 JSON 安全结构，避免 numpy.ndarray 等对象导致序列化失败
            safe_result_data = result_data
            try:
                safe_result_data = json.loads(
                    json.dumps(result_data, ensure_ascii=False, default=lambda o: None)
                )
            except Exception as e:
                logger.warning(f'⚠️ 项目结果JSON序列化失败，将使用精简结果结构: {e}')
                try:
                    va = result_data.get('vision_analysis') or {}
                except Exception:
                    va = {}
                safe_result_data = {
                    'vision_analysis': {
                        'scenes': va.get('scenes'),
                        'descriptions': va.get('descriptions'),
                        'summary': va.get('summary')
                    },
                    'script': result_data.get('script'),
                    'audio_path': result_data.get('audio_path'),
                    'sync_results': result_data.get('sync_results'),
                    'output_path': result_data.get('output_path')
                }
            
            # 保存到项目
            self.db_manager.update_project(project_id, {
                'result': safe_result_data,
                'status': 'completed'
            })
            
            logger.info(f'✅ 项目处理完成: {project_id}')
            
            return {
                'code': 0,
                'msg': '处理完成',
                'data': {
                    'task_id': task_id,
                    'output_path': output_path,
                    'result': safe_result_data
                }
            }
            
        except Exception as e:
            logger.error(f'❌ 处理失败: {e}', exc_info=True)
            try:
                self.db_manager.update_task_status(task_id, 'failed', error_message=str(e))
            except Exception:
                pass
            return {'code': 1, 'msg': f'处理失败: {str(e)}', 'data': None}
    
    def _analyze_video(self, video_path: str, task_id: str, config: Optional[Dict] = None) -> Optional[Dict]:
        """步骤1: 视频画面分析"""
        try:
            # 确保配置始终为字典，避免 NameError
            if config is None:
                config = {}

            if not self.vision_analyzer:
                logger.warning('⚠️ 视觉分析引擎不可用，使用简化分析')
                return self._simple_video_analysis(video_path)
            
            # ========= 基于文件签名的视频分析缓存 =========
            cache_file = None
            try:
                # 使用绝对路径 + 文件大小 + 修改时间 构建稳定签名
                video_abs = os.path.abspath(video_path)
                stat = os.stat(video_abs)
                sig_src = f"{video_abs}|{stat.st_size}|{int(stat.st_mtime)}"
                cache_key = hashlib.md5(sig_src.encode('utf-8')).hexdigest()

                analysis_dir = TEMP_DIR / 'analysis'
                analysis_dir.mkdir(parents=True, exist_ok=True)
                cache_file = analysis_dir / f'frame_analysis_{cache_key}.json'
            except Exception as e:
                logger.warning(f'⚠️ 计算视频签名失败，将不使用缓存: {e}')
                cache_file = None

            # 1. 优先尝试复用缓存结果
            if cache_file and cache_file.exists():
                try:
                    with cache_file.open('r', encoding='utf-8') as f:
                        cached = json.load(f)
                    if isinstance(cached, dict) and cached.get('scenes') is not None:
                        logger.info(f'📂 复用视频分析缓存: {cache_file}')
                        self._emit_progress(task_id, 25, '已复用视频分析缓存')
                        return cached
                except Exception as e:
                    logger.warning(f'⚠️ 读取视频分析缓存失败，将重新分析: {e}')

            logger.info('🎬 开始视频画面分析...')

            # 2. 使用视觉分析引擎
            results = self.vision_analyzer.analyze_video(video_path, max_keyframes=15)

            # 3. 如果配置了多模型，使用多模型增强描述
            keyframes = (results or {}).get('keyframes') or []
            descriptions = (results or {}).get('descriptions') or []
            if self.multi_model and self.config_manager and keyframes and descriptions:
                logger.info('🤖 使用多模型增强画面描述...')
                analysis_dir = TEMP_DIR / 'analysis'
                try:
                    analysis_dir.mkdir(parents=True, exist_ok=True)
                except Exception:
                    analysis_dir = TEMP_DIR

                for i, desc in enumerate(descriptions):
                    if i >= len(keyframes):
                        break

                    frame_info = keyframes[i] or {}
                    frame = frame_info.get('image')
                    img_path: Optional[Path] = None

                    # 1）优先使用内存中的图像帧写入临时文件
                    if frame is not None:
                        try:
                            ts = frame_info.get('timestamp') or i
                            img_path = analysis_dir / f'mm_keyframe_{int(ts)}_{i}.jpg'

                            save_ok = False
                            try:
                                # frame 为 numpy.ndarray 时直接写入，cv2.imwrite 返回 bool
                                save_ok = bool(cv2.imwrite(str(img_path), frame))
                            except Exception:
                                save_ok = False

                            if (not save_ok) or (not img_path.exists()):
                                logger.warning(f'⚠️ 关键帧图片保存失败，跳过多模型分析: index={i}, path={img_path}')
                                img_path = None
                        except Exception as e:
                            logger.warning(f'⚠️ 关键帧图片写入异常，跳过该帧多模型分析: index={i}, err={e}')
                            img_path = None

                    # 2）如果帧数据为空，尝试使用帧信息里已有的图片路径
                    if img_path is None:
                        try:
                            candidate = frame_info.get('image_path') or frame_info.get('path') or frame
                            if isinstance(candidate, str) and os.path.exists(candidate):
                                img_path = Path(candidate)
                        except Exception:
                            img_path = None

                    # 3）最终仍没有可用图片文件，则跳过该帧的多模型分析，避免向通义传递不存在的路径
                    if img_path is None or not img_path.exists():
                        continue

                    try:
                        enhanced_desc = self.multi_model.analyze_image(
                            str(img_path),
                            (
                                "请详细、准确地描述这个画面的内容。\n"
                                "重要要求：\n"
                                "1. 如果画面中有动物，必须准确识别其种类（如老虎、狮子、斑马等），不得臆测或替换\n"
                                "2. 如果看不清楚或不确定，直接说'不清楚'或'模糊'，不要乱猜\n"
                                "3. 描述画面中的场景、主体、动作、情绪和氛围\n"
                                "4. 用简洁准确的中文，不超过100字"
                            )
                        )
                        desc['enhanced_description'] = enhanced_desc
                        self._emit_progress(task_id, 10 + i * 2, f'分析关键帧 {i+1}...')
                    except Exception as e:
                        logger.warning(f'⚠️ 多模型增强关键帧描述失败: {e}')

            if not results:
                logger.error('❌ 视频分析返回空结果')
                return None

            logger.info(f'✅ 视频分析完成: {len(results.get("scenes", []))}个场景, {len(results.get("keyframes", []))}个关键帧')

            # 4. 智能场景筛选：评估场景质量并筛选高分场景
            try:
                from backend.engine.scene_scorer import score_and_filter_scenes
                
                scenes = results.get('scenes', [])
                # 获取目标时长（用于智能筛选）
                target_duration = config.get('target_duration') or config.get('target_duration_seconds')
                if target_duration:
                    try:
                        target_duration = float(target_duration)
                    except Exception:
                        target_duration = None
                
                # 收集对象检测结果
                objects_list = [obj_info.get('objects', []) for obj_info in results.get('objects', [])]
                
                # 执行评分和筛选
                if scenes and len(scenes) > 3:  # 只在场景数>3时才筛选
                    logger.info(f'🧠 开始智能场景筛选: 原始{len(scenes)}个场景')
                    filtered_scenes = score_and_filter_scenes(
                        scenes=scenes,
                        video_path=video_path,
                        objects_list=objects_list if objects_list else None,
                        target_duration=target_duration
                    )
                    
                    if filtered_scenes and len(filtered_scenes) < len(scenes):
                        # 筛选成功，更新结果
                        results['scenes'] = filtered_scenes
                        results['original_scenes'] = scenes  # 保留原始场景供参考
                        logger.info(
                            f'✅ 智能筛选完成: '
                            f'{len(scenes)}个场景 → {len(filtered_scenes)}个高质量场景, '
                            f'平均评分: {np.mean([s.get("score", 0) for s in filtered_scenes]):.1f}'
                        )
                    else:
                        logger.info('📌 场景质量均衡，无需筛选')
                else:
                    logger.info(f'📌 场景数量较少({len(scenes)})，跳过筛选')
                    
            except Exception as e:
                logger.warning(f'⚠️ 智能场景筛选失败，使用原始场景: {e}')

            # 5. 写入缓存（去除不可序列化字段）
            if cache_file:
                try:
                    safe_results = json.loads(
                        json.dumps(results, ensure_ascii=False, default=lambda o: None)
                    )
                    with cache_file.open('w', encoding='utf-8') as f:
                        json.dump(safe_results, f, ensure_ascii=False)
                    logger.info(f'💾 已写入视频分析缓存: {cache_file}')
                except Exception as e:
                    logger.warning(f'⚠️ 写入视频分析缓存失败: {e}')

            return results
            
        except Exception as e:
            logger.error(f'❌ 视频分析失败: {e}')
            return None

    def _generate_script(self, vision_results: Dict, config: Dict, task_id: str) -> Optional[Dict]:
        """步骤2: AI生成解说文案"""
        try:
            # 1. 根据前端传入的 llm 选择动态切换当前使用的 LLM 模型
            llm_from_config = None
            try:
                llm_from_config = (config.get('llm') or config.get('llm_model') or '').strip()  # type: ignore[arg-type]
            except Exception:
                llm_from_config = None

            if self.global_state and llm_from_config:
                try:
                    # 切换活动 LLM 模型（会重置内部 ScriptGenerator 实例）
                    self.global_state.set_active_llm_model(llm_from_config)
                except Exception as e:
                    logger.warning(f'⚠️ 切换LLM模型失败: {e}')

            # 2. 每次生成前都从全局状态获取最新的 ScriptGenerator，避免使用过期实例
            script_generator = None
            if self.global_state:
                try:
                    script_generator = self.global_state.get_script_generator()
                except Exception as e:
                    logger.error(f'❌ 获取文案生成引擎失败: {e}', exc_info=True)
            else:
                script_generator = self.script_generator

            if not script_generator:
                logger.warning('⚠️ 文案生成引擎不可用，使用模板文案')
                return self._template_script(vision_results)

            logger.info('📝 开始生成解说文案...')
            
            # 获取风格
            style = config.get('style', 'professional')
            narration_mode = config.get('narration_mode', 'general')
            mode_lower = (narration_mode or 'general').lower()

            # 根据解说类型自动选择合适的开头钩子类型
            # 默认使用悬念式
            hook_type = 'suspense'
            if mode_lower in ('romance', 'animation_3rd'):
                # 情感/怀旧类，更适合情感共鸣型开头
                hook_type = 'empathy'
            elif mode_lower == 'film_3rd':
                # 第三人称影视解说，突出剧情反转
                hook_type = 'reversal'
            elif mode_lower == 'documentary':
                # 纪录片风，适合问题引导型或信息型开头
                hook_type = 'question'
            elif mode_lower == 'film_1st':
                # 第一人称强代入，悬念式更抓人
                hook_type = 'suspense'
            elif mode_lower == 'suspense_twist':
                # 悬疑反转专用，优先用悬念式
                hook_type = 'suspense'

            # 整理前端传入的高级配置，用于构建自定义创作要求
            template = config.get('template') or 'custom'
            emotion_tone = config.get('emotion_tone') or config.get('emotionTone') or 'neutral'
            structure = config.get('structure') or 'complete'
            target_audience = config.get('target_audience') or 'general'
            length = config.get('length') or 'medium'
            creativity = config.get('creativity') or 'moderate'

            # 目标时长：优先使用前端传入的 target_duration_seconds，其次使用视觉分析中的 duration
            target_duration = config.get('target_duration_seconds') or vision_results.get('duration')
            try:
                if target_duration is not None:
                    target_duration = float(target_duration)
            except Exception:
                target_duration = vision_results.get('duration')

            # 当用户选择目标时长小于整段视频时，仅基于前 target_duration 秒的场景生成文案
            vision_for_script = vision_results
            try:
                full_duration = None
                if 'duration' in vision_results:
                    full_duration = float(vision_results.get('duration') or 0.0)
            except Exception:
                full_duration = None

            if target_duration and full_duration and target_duration < full_duration - 0.5:
                try:
                    scenes = vision_results.get('scenes') or []
                    new_scenes = []
                    for idx, sc in enumerate(scenes):
                        try:
                            sc_start = float(sc.get('start_time', 0.0) or 0.0)
                            sc_end = float(sc.get('end_time', sc_start) or sc_start)
                        except Exception:
                            sc_start, sc_end = 0.0, 0.0

                        # 完全超出目标时长的场景直接丢弃
                        if sc_start >= target_duration:
                            break

                        # 与目标时长有交集的最后一个场景，截断到目标时长
                        if sc_end > target_duration:
                            sc_end = target_duration

                        if sc_end <= sc_start:
                            continue

                        sc_new = dict(sc)
                        sc_new['start_time'] = float(sc_start)
                        sc_new['end_time'] = float(sc_end)
                        sc_new['duration'] = float(sc_end - sc_start)
                        new_scenes.append(sc_new)

                    # 按场景数量截断描述/情绪信息，避免与场景错位
                    desc_list = (vision_results.get('descriptions') or [])[:len(new_scenes)]
                    emo_list = (vision_results.get('emotions') or [])[:len(new_scenes)]
                    obj_list = (vision_results.get('objects') or [])[:len(new_scenes)]

                    vision_for_script = dict(vision_results)
                    vision_for_script['scenes'] = new_scenes
                    vision_for_script['descriptions'] = desc_list
                    vision_for_script['emotions'] = emo_list
                    vision_for_script['objects'] = obj_list
                    vision_for_script['duration'] = float(target_duration)
                except Exception as e:
                    logger.warning(f'⚠️ 基于目标时长截断场景失败，将使用完整视频分析: {e}')

            # 将结构、长度、创意度等枚举值映射为更易理解的中文描述
            structure_map = {
                'complete': '完整起承转合结构',
                'outline': '提纲式要点结构',
                'three_act': '三幕式结构（开端-发展-高潮/结局）'
            }
            length_map = {
                'short': '整体字数偏短，控制在约100-200字',
                'medium': '标准长度，控制在约200-400字',
                'long': '内容更详细，控制在约400-800字'
            }
            creativity_map = {
                'low': '创意度偏保守，以事实和画面为主，少用夸张和网络梗',
                'moderate': '适度创意，在保证信息准确的前提下增强吸引力',
                'high': '创意度较高，可以合理虚构细节增强故事性，但不能违背画面内容'
            }
            audience_map = {
                'general': '面向大众观众，语言口语化、易懂',
                'kids': '面向儿童或家庭用户，语言温和、积极、避免复杂表达',
                'professional': '面向专业人士，可适度使用专业术语、逻辑更严谨'
            }

            structure_desc = structure_map.get(str(structure), str(structure))

            base_chars = None
            if target_duration:
                try:
                    base_chars = max(60, int(float(target_duration) * 3.5))
                except Exception:
                    base_chars = None

            if base_chars:
                length_str = str(length)
                if length_str == 'short':
                    min_chars = int(base_chars * 0.6)
                    max_chars = int(base_chars * 0.85)
                elif length_str == 'long':
                    min_chars = int(base_chars * 1.0)
                    max_chars = int(base_chars * 1.35)
                elif length_str == 'auto':
                    min_chars = int(base_chars * 0.8)
                    max_chars = int(base_chars * 1.1)
                else:
                    min_chars = int(base_chars * 0.75)
                    max_chars = int(base_chars * 1.05)
                length_desc = f'整体字数控制在约{min_chars}-{max_chars}字，使正常语速朗读时长尽量贴近剪辑后目标视频时长（约{target_duration:.0f}秒）。'
            else:
                length_desc = length_map.get(str(length), str(length))

            creativity_desc = creativity_map.get(str(creativity), str(creativity))
            audience_desc = audience_map.get(str(target_audience), str(target_audience))

            # 组合成交给大模型的自定义创作要求
            custom_requirements_lines = [
                f"- 模板/类型偏好：{template}（可以据此选择更贴合的叙事风格，例如影视解说/动画解说/纪录片解说等）",
                f"- 目标受众：{audience_desc}",
                f"- 文稿结构：{structure_desc}",
                f"- 文稿长度：{length_desc}",
                f"- 创意程度：{creativity_desc}",
                f"- 情感基调：整体情绪基调倾向于“{emotion_tone}”，请在措辞和节奏上体现这一点。"
            ]
            if target_duration:
                custom_requirements_lines.append(
                    f"- 目标整体时长：约{float(target_duration):.0f}秒，请控制文稿节奏和信息密度，使朗读时长与该目标大致匹配。"
                )

            custom_prompt = "\n".join(custom_requirements_lines)

            logger.info(f'📝 调用文案生成器，目标时长: {target_duration}秒')
            script = script_generator.generate_script(
                vision_analysis=vision_for_script,
                style=style,
                duration=target_duration,
                narration_mode=narration_mode,
                custom_prompt=custom_prompt,
                hook_type=hook_type
            )
            
            # 立即检查生成的文案字数
            if script and script.get('segments'):
                total_chars = sum(len(seg.get('text', '')) for seg in script['segments'])
                estimated_duration = total_chars / 3.5
                logger.info(
                    f'📊 文案生成完成: 总字数={total_chars}字, '
                    f'预计时长={estimated_duration:.1f}秒, '
                    f'目标时长={target_duration}秒'
                )
                if target_duration and estimated_duration > target_duration * 1.2:
                    logger.error(
                        f'❌ 文案严重超标！预计{estimated_duration:.1f}秒 > 目标{target_duration}秒的1.2倍，'
                        f'字数控制可能失败！'
                    )

            if not isinstance(script, dict):
                try:
                    script = json.loads(script)
                except Exception:
                    logger.warning('⚠️ 文案生成结果不是结构化JSON，回退到模板文案')
                    return self._template_script(vision_results)

            return script

        except Exception as e:
            logger.error(f'❌ 文案生成失败: {e}', exc_info=True)
            # 出错时退回规则模板文案，避免直接返回None
            return self._template_script(vision_results)
    
    def _generate_voiceover(self, script: Dict[str, Any], config: Dict[str, Any], task_id: str) -> Optional[str]:
        """步骤3: 智能配音

        供完整流程 process_video 与 /api/commentary/generate-voiceover 调用。
        返回相对项目根目录的路径，例如: "output/commentary_audio_xxx.mp3"。
        """
        try:
            if not self.tts_engine:
                logger.warning('⚠️ TTS引擎不可用')
                return None

            # 聚合脚本文本（支持脚本为结构化字典或纯字符串）
            full_text = ''

            # 1）优先按结构化 dict 解析（title + opening + segments + closing）
            if isinstance(script, dict):
                try:
                    parts = []
                    title = script.get('title') or ''
                    if title:
                        parts.append(title)
                    opening = script.get('opening') or ''
                    if opening:
                        parts.append(opening)
                    for seg in script.get('segments') or []:
                        text = seg.get('text') or ''
                        if text:
                            parts.append(text)
                    closing = script.get('closing') or ''
                    if closing:
                        parts.append(closing)
                    full_text = "\n".join(parts).strip()
                except Exception as e:
                    # 结构化解析失败时，退回到纯文本模式，避免 AttributeError: 'str' object has no attribute 'get'
                    logger.warning(f'⚠️ 脚本结构化解析失败，将按纯文本处理: {e}')
                    try:
                        full_text = str(script).strip()
                    except Exception:
                        full_text = ''

            # 2）如果不是 dict，或上一步未能成功生成文本，则退回到字符串处理
            if not full_text:
                if isinstance(script, str):
                    full_text = script.strip()
                else:
                    try:
                        full_text = str(script).strip()
                    except Exception:
                        full_text = ''

            if not full_text:
                raise Exception('脚本内容为空，无法生成配音')

            # 获取音色参数，不使用 or 运算符避免空字符串被当作 False
            voice = config.get('voice')
            if not voice:  # 只在真正为空时才用默认值
                voice = 'zh-CN-XiaoxiaoNeural'
            logger.info(f'🎤 用户选择的音色: {voice}')

            # 前端可选指定首选TTS引擎（voice-clone / voice-pro / pyttsx3 / 其它在线TTS）
            preferred_engine = None
            voice_clone_mode = False
            try:
                raw_engine = (config.get('tts_engine') or config.get('ttsEngine') or '').strip().lower()
            except Exception:
                raw_engine = ''

            if raw_engine in ('voice-clone', 'voice_clone', 'voiceclone', 'local-clone', 'vc'):
                voice_clone_mode = True
            elif raw_engine in ('voice-pro', 'voice_pro', 'voicepro'):
                preferred_engine = 'voice-pro'
            elif raw_engine in ('azure', 'azure-tts'):
                # 原创解说流程不再直接调用在线 Azure TTS，这里退回到本地引擎
                preferred_engine = 'pyttsx3'
            elif raw_engine in ('gtts', 'google', 'google-tts'):
                # gTTS 依赖 Google 网络，在当前环境下易失败，统一退回到本地引擎
                preferred_engine = 'pyttsx3'
            elif raw_engine in ('pyttsx3', 'local', 'offline'):
                preferred_engine = 'pyttsx3'
            elif raw_engine in ('edge', 'edge-tts'):
                # Edge-TTS 在国内网络下易403，这里统一退回到本地引擎
                preferred_engine = 'pyttsx3'

            # Voice Clone 模式：优先尝试本地语音克隆链路，失败时再退回普通TTS（本地引擎）
            if voice_clone_mode and getattr(self, 'voice_clone_engine', None):
                logger.info(f'🎤 用户选择了 Voice Clone 引擎，音色ID: {voice}')
                vc_rel = self._generate_voiceover_with_voice_clone(full_text, voice, task_id)
                if vc_rel:
                    return vc_rel
                else:
                    logger.warning(f'⚠️ Voice Clone 生成失败，将使用普通TTS（本地引擎）备选')
                    # Voice Clone 失败时，如果 voice 是 clone-* 格式，需要转换为普通TTS支持的音色
                    if voice.startswith('clone-'):
                        voice = 'zh-CN-XiaoxiaoNeural'
                        logger.info(f'🔄 已将Voice Clone音色转换为普通中文音色: {voice}')
            elif voice_clone_mode:
                logger.warning(f'⚠️ Voice Clone 引擎未初始化，将使用普通TTS（本地引擎）备选')
                if voice.startswith('clone-'):
                    voice = 'zh-CN-XiaoxiaoNeural'
                    logger.info(f'🔄 已将Voice Clone音色转换为普通中文音色: {voice}')

            # 输出到项目根目录下的 output/commentary_audio_*.mp3，便于前端通过 /output 静态路由访问
            file_name = f"commentary_audio_{int(time.time())}_{uuid.uuid4().hex[:6]}.mp3"
            rel_path = f"output/{file_name}"
            out_path = PROJECT_ROOT / 'output' / file_name
            out_path.parent.mkdir(parents=True, exist_ok=True)

            success = False

            # 原创解说流程强制使用本地 pyttsx3 引擎，不再调用 Edge-TTS / gTTS / Azure 等在线引擎
            available = list(getattr(self.tts_engine, 'available_engines', []) or [])
            if 'pyttsx3' not in available:
                logger.warning('⚠️ 全局引擎列表中未声明 pyttsx3，将直接尝试调用本地 pyttsx3 引擎')

            engine0 = 'pyttsx3'

            # 1）首选且唯一的 TTS 引擎：本地 pyttsx3
            try:
                logger.info(f'🎵 正在调用 {engine0} 引擎，音色: {voice}')
                success = self.tts_engine.synthesize(
                    text=full_text,
                    output_path=str(out_path),
                    engine=engine0,
                    voice=voice,
                    rate='+0%',
                    volume='+0%'
                )
                if success:
                    logger.info(f'✅ {engine0} 引擎合成成功')
            except Exception as e:
                logger.error(f"❌ 首选 TTS 引擎({engine0}) 合成失败: {e}", exc_info=True)
                success = False

            # 2）额外的兜底再尝试一次 pyttsx3（极端情况下前一次调用写盘失败）
            if not success or not out_path.exists():
                try:
                    logger.info('🎵 首次调用失败，再次尝试本地 pyttsx3 引擎兜底')
                    success = self.tts_engine.synthesize(
                        text=full_text,
                        output_path=str(out_path),
                        engine='pyttsx3',
                        voice=voice,
                        rate='+0%',
                        volume='+0%'
                    )
                except Exception as e:
                    logger.error(f"❌ 本地 pyttsx3 兜底合成仍然失败: {e}", exc_info=True)
                    success = False

            if not success or not out_path.exists():
                raise Exception('配音文件生成失败')

            # 读取配音实际时长，用于重新调整字幕时间轴（直接使用 ffprobe，兼容音频文件）
            try:
                cmd = [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    str(out_path)
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                actual_audio_duration = 0.0
                if result.returncode == 0:
                    dur_str = (result.stdout or '').strip()
                    try:
                        if dur_str:
                            actual_audio_duration = float(dur_str)
                    except Exception:
                        actual_audio_duration = 0.0

                if actual_audio_duration > 0:
                    logger.info(f'✅ 配音生成完成: {rel_path}，实际时长: {actual_audio_duration:.2f}秒')
                    # 将实际时长保存到全局变量，供后续字幕调整使用
                    if not hasattr(self, '_audio_duration_cache'):
                        self._audio_duration_cache = {}
                    self._audio_duration_cache[task_id] = actual_audio_duration
                else:
                    logger.warning('⚠️ ffprobe 未能读取配音时长，将按脚本文本估算')
            except Exception as e:
                logger.warning(f'⚠️ 无法读取配音时长(ffprobe调用失败): {e}')
            
            logger.info(f'✅ 配音生成完成: {rel_path}')
            return rel_path

        except Exception as e:
            logger.error(f'❌ 配音生成失败: {e}', exc_info=True)
            return None
    
    def _generate_voiceover_with_voice_clone(self, full_text: str, voice_id: str, task_id: str) -> Optional[str]:
        """使用本地 Voice Clone 引擎生成配音，返回相对项目根目录的路径。"""
        try:
            vc_engine = getattr(self, 'voice_clone_engine', None)
            if not vc_engine:
                logger.error('❌ Voice Clone 引擎未初始化，无法使用本地克隆音色')
                return None
            
            # 再次检查引擎状态
            status = vc_engine.get_status()
            if not status.get('ready'):
                logger.error(
                    f'❌ Voice Clone 引擎状态不就绪: '
                    f'exe_ok={status.get("executable_ok")}, model_ok={status.get("model_ok")}, '
                    f'exe={status.get("executable_path")}, model={status.get("model_path")}'
                )
                return None
            
            if not self.tts_engine:
                logger.error('❌ TTS 引擎不可用，无法为 Voice Clone 生成基础音频')
                return None

            vc_dir = OUTPUTS_DIR / 'voice_clone_commentary'
            vc_dir.mkdir(parents=True, exist_ok=True)

            ts = int(time.time() * 1000)
            tts_path = vc_dir / f'tts_{ts}.mp3'
            clone_path = vc_dir / f'clone_{ts}.wav'

            target_voice = self._map_voice_clone_id(voice_id)
            logger.info(f'🎙️ 原创解说 VoiceClone: len={len(full_text)}, target={target_voice}')

            # 1）先用本地 pyttsx3 合成基础音频（稳定、离线）
            try:
                logger.info(f'🎤 正在生成Voice Clone基础音频: {len(full_text)}字')
                tts_ok = self.tts_engine.synthesize(
                    text=full_text,
                    output_path=str(tts_path),
                    engine='pyttsx3'
                )
                if tts_ok and tts_path.exists():
                    logger.info(f'✅ 基础音频生成成功: {tts_path}')
                else:
                    logger.error(f'❌ 基础音频生成失败: tts_ok={tts_ok}, exists={tts_path.exists()}')
                    return None
            except Exception as e:
                logger.error(f'❌ Voice Clone 基础 TTS 合成失败: {e}', exc_info=True)
                return None

            # 2）调用本地 Voice Clone 引擎进行克隆
            try:
                logger.info(f'🎵 正在调用Voice Clone引擎，目标音色: {target_voice}')
                out_path = vc_engine.clone_voice(
                    source_audio=str(tts_path),
                    target_voice=target_voice,
                    output_path=str(clone_path)
                )
                if not out_path:
                    logger.error('❌ Voice Clone 引擎返回空路径')
                    return None
                if not Path(out_path).exists():
                    logger.error(f'❌ Voice Clone 输出文件不存在: {out_path}')
                    return None
                logger.info(f'✅ Voice Clone 克隆成功: {out_path}')
            except Exception as e:
                logger.error(f'❌ Voice Clone 克隆调用失败: {e}', exc_info=True)
                return None

            p = Path(out_path).resolve()
            try:
                rel = p.relative_to(PROJECT_ROOT)
                rel_str = rel.as_posix()
            except Exception:
                # 兜底：如果路径在 TEMP outputs 下，尽量构造相对路径
                try:
                    rel = p.relative_to(OUTPUTS_DIR)
                    rel_str = f"temp/outputs/{rel.as_posix()}"
                except Exception:
                    rel_str = p.as_posix()

            logger.info(f'✅ 原创解说 VoiceClone 配音生成完成: {rel_str}')
            return rel_str

        except Exception as e:
            logger.error(f'❌ 原创解说 VoiceClone 配音生成失败: {e}', exc_info=True)
            return None
    
    def _sync_all(self, video_path: str, audio_path: str, script: Dict, 
                  vision_results: Dict, task_id: str) -> Optional[Dict]:
        """步骤4: 三同步处理"""
        try:
            if not self.sync_engine:
                logger.warning('⚠️ 同步引擎不可用')
                return None
            
            # 在同步前，先根据配音实际时长重新调整字幕时间轴
            actual_audio_duration = getattr(self, '_audio_duration_cache', {}).get(task_id)
            if actual_audio_duration and script and isinstance(script, dict):
                segments = script.get('segments') or []
                if segments:
                    # 计算原始 segments 的总时长
                    original_duration = max(seg.get('end_time', 0) for seg in segments) if segments else 0
                    
                    if original_duration > 0 and abs(actual_audio_duration - original_duration) > 1.0:
                        logger.warning(
                            f'⚠️ 配音实际时长({actual_audio_duration:.2f}s)与原始场景时长({original_duration:.2f}s)'
                            f'差异较大，重新调整字幕时间轴'
                        )
                        
                        # 按比例调整每个 segment 的时间
                        scale = actual_audio_duration / original_duration
                        for seg in segments:
                            try:
                                old_start = float(seg.get('start_time', 0))
                                old_end = float(seg.get('end_time', old_start))
                                seg['start_time'] = old_start * scale
                                seg['end_time'] = old_end * scale
                            except Exception as e:
                                logger.warning(f'⚠️ 调整segment时间失败: {e}')
                        
                        logger.info(f'✅ 已根据配音实际时长重新调整字幕时间轴')
            
            logger.info('🔄 开始执行三同步...')
            
            # 执行三同步
            sync_results = self.sync_engine.sync_all(
                video_path=video_path,
                audio_path=audio_path,
                script=script,
                vision_analysis=vision_results
            )
            
            logger.info(f'✅ 三同步完成，质量评分: {sync_results.get("sync_quality", 0):.2f}')
            
            return sync_results
            
        except Exception as e:
            logger.error(f'❌ 三同步失败: {e}')
            return None
    
    def _compose_final_video(self, video_path: str, audio_path: str, script: Dict,
                            sync_results: Dict, config: Dict, task_id: str) -> Optional[str]:
        """步骤5: 合成最终视频"""
        try:
            logger.info('🎬 开始合成最终视频...')

            base_dir = PROJECT_ROOT
            output_dir = base_dir / 'output' / 'commentary'
            output_dir.mkdir(parents=True, exist_ok=True)

            video_path_obj = Path(video_path)
            if not video_path_obj.is_absolute():
                video_path_obj = base_dir / video_path_obj

            audio_path_obj = Path(audio_path)
            if not audio_path_obj.is_absolute():
                audio_path_obj = base_dir / audio_path_obj

            # 获取配音实际时长，用于剪辑视频和调整字幕
            audio_duration = 0.0
            try:
                cmd = [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    str(audio_path_obj)
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    dur_str = (result.stdout or '').strip()
                    if dur_str:
                        audio_duration = float(dur_str)
                logger.info(f'🎵 配音实际时长: {audio_duration:.2f}秒')
            except Exception as e:
                logger.warning(f'⚠️ 无法获取配音时长: {e}')

            # 如果有配音时长，先裁剪视频到配音时长
            clipped_video_path = str(video_path_obj)
            if audio_duration > 0:
                try:
                    from backend.engine.video_clipper import VideoClipper
                    clipper = VideoClipper()
                    clipped_video_path = str(output_dir / f"clipped_{task_id[:8]}.mp4")
                    clipper.clip_video_by_timestamp(
                        input_video=str(video_path_obj),
                        output_video=clipped_video_path,
                        start_time="00:00:00.000",
                        end_time=f"00:00:{audio_duration:06.3f}"
                    )
                    logger.info(f'✂️ 已将视频剪辑到配音时长: {audio_duration:.2f}秒')
                except Exception as e:
                    logger.warning(f'⚠️ 视频剪辑失败，将使用原始视频: {e}')
                    clipped_video_path = str(video_path_obj)

            subtitle_path: Optional[str] = None
            auto_subtitle = bool(config.get('auto_subtitle', True))

            if auto_subtitle:
                narration_script: Optional[Dict[str, Any]] = None
                subtitle_segments = None
                try:
                    subtitle_segments = (sync_results or {}).get('audio_text_sync', {}).get('subtitle_segments')
                except Exception:
                    subtitle_segments = None

                # 计算脚本预估时长
                script_duration = 0.0
                if script.get('segments'):
                    last_segment = script['segments'][-1]
                    script_duration = float(last_segment.get('end_time', 0.0))

                # 时间轴缩放因子：如果配音时长与脚本时长不一致，需要调整字幕时间
                time_scale = 1.0
                if audio_duration > 0 and script_duration > 0:
                    time_scale = audio_duration / script_duration
                    if abs(time_scale - 1.0) > 0.01:  # 差异超过1%才调整
                        logger.info(f'⏰ 配音时长({audio_duration:.2f}s)与脚本时长({script_duration:.2f}s)不一致，时间轴缩放: {time_scale:.4f}')

                if subtitle_segments:
                    narrations = []
                    for seg in subtitle_segments:
                        start = float(seg.get('start', seg.get('start_time', 0.0)))
                        end = float(seg.get('end', seg.get('end_time', start)))
                        # 应用时间轴缩放
                        start *= time_scale
                        end *= time_scale
                        # 确保结束时间不超过配音时长
                        if end > audio_duration:
                            end = audio_duration
                        text = seg.get('text', '')
                        time_range = f"{start:.3f}s-{end:.3f}s"
                        narrations.append({'time_range': time_range, 'text': text})
                    if narrations:
                        narration_script = {'narrations': narrations}
                else:
                    segments = script.get('segments') or []
                    narrations = []
                    for seg in segments:
                        start = float(seg.get('start_time', 0.0))
                        end = float(seg.get('end_time', start))
                        # 应用时间轴缩放
                        start *= time_scale
                        end *= time_scale
                        # 确保结束时间不超过配音时长
                        if end > audio_duration:
                            end = audio_duration
                        text = seg.get('text', '')
                        time_range = f"{start:.3f}s-{end:.3f}s"
                        narrations.append({'time_range': time_range, 'text': text})
                    if narrations:
                        narration_script = {'narrations': narrations}

                if narration_script:
                    try:
                        srt_path = output_dir / f"commentary_{int(time.time())}_{uuid.uuid4().hex[:6]}.srt"
                        generator = SubtitleGenerator()
                        subtitle_path = generator.generate_srt_from_script(narration_script, str(srt_path))
                    except Exception as se:
                        logger.error(f'❌ 生成字幕失败: {se}')
                        subtitle_path = None

            bgm_path: Optional[str] = None
            if config.get('auto_bgm'):
                # 优先使用配置中的BGM路径
                bgm_value = config.get('bgm')
                if bgm_value:
                    bgm_obj = Path(bgm_value)
                    if not bgm_obj.is_absolute():
                        bgm_obj = base_dir / bgm_obj
                    if bgm_obj.exists():
                        bgm_path = str(bgm_obj)
                    else:
                        logger.warning(f'指定的BGM文件不存在: {bgm_obj}')
                else:
                    # 未显式指定BGM时，尝试使用默认背景音乐 backend/assets/audio/default_bgm.mp3
                    default_bgm = AUDIO_DIR / 'default_bgm.mp3'
                    if default_bgm.exists():
                        bgm_path = str(default_bgm)
                        logger.info(f'🎵 自动BGM已启用，使用默认背景音乐: {default_bgm}')
                    else:
                        candidates = []
                        try:
                            for ext in ('.mp3', '.wav', '.m4a', '.flac', '.ogg'):
                                candidates.extend(AUDIO_DIR.glob(f'**/*{ext}'))
                        except Exception as se:
                            logger.warning(f'自动BGM搜索资源失败: {se}')
                            candidates = []

                        if candidates:
                            try:
                                candidates = sorted(candidates, key=lambda p: str(p))
                            except Exception:
                                pass

                            preferred = [p for p in candidates if p.name.lower().startswith(('bgm_', 'default_'))]
                            chosen = preferred[0] if preferred else candidates[0]
                            bgm_path = str(chosen)
                            logger.info(f'🎵 自动BGM已启用，从音频资源目录选择: {chosen}')
                        else:
                            logger.warning(
                                f'自动BGM已启用，但未提供bgm且默认BGM文件不存在，且音频资源目录为空: {AUDIO_DIR}'
                            )

            # 计算目标时长：优先使用前端传入的 target_duration_seconds，并结合源视频时长进行夹紧
            target_duration: Optional[float] = None
            source_duration: Optional[float] = None

            try:
                td_val = config.get('target_duration_seconds')
                if td_val is not None:
                    target_duration = float(td_val)
            except Exception:
                target_duration = None

            try:
                sd_val = config.get('source_duration_seconds')
                if sd_val is not None:
                    source_duration = float(sd_val)
            except Exception:
                source_duration = None

            # 如未显式提供源视频时长，则尝试在后端探测一次
            if source_duration is None or source_duration <= 0:
                try:
                    vp = VideoProcessor()
                    info = vp.get_video_info(str(video_path_obj)) or {}
                    src_dur = float(info.get('duration') or 0.0)
                    if src_dur > 0:
                        source_duration = src_dur
                except Exception as e:
                    logger.warning(f'⚠️ 获取源视频时长失败，将跳过基于源时长的夹紧: {e}')

            max_duration_for_merge: Optional[float] = None
            if target_duration is not None:
                # 基本下限保护
                if target_duration < 1.0:
                    target_duration = 1.0
                # 不超过源视频
                if source_duration and source_duration > 0 and target_duration > source_duration:
                    logger.info(
                        '目标时长 %.2fs 大于源视频时长 %.2fs，已在合成阶段自动夹紧',
                        target_duration,
                        source_duration,
                    )
                    target_duration = source_duration

                max_duration_for_merge = target_duration

            output_file = output_dir / f"commentary_{int(time.time())}_{uuid.uuid4().hex[:6]}.mp4"

            # 读取字幕样式相关配置：样式预设 / 位置 / 字号
            subtitle_style_name = (config.get('subtitle_style')
                                   or config.get('subtitleStyle')
                                   or 'large')
            subtitle_position_conf = config.get('subtitle_position') or config.get('subtitlePosition')
            subtitle_font_size_conf = config.get('subtitle_font_size') or config.get('subtitleFontSize')
            subtitle_font_conf = config.get('subtitle_font') or config.get('subtitleFont')
            subtitle_color_conf = config.get('subtitle_color') or config.get('subtitleColor')
            subtitle_bg_color_conf = config.get('subtitle_bg_color') or config.get('subtitleBgColor')
            subtitle_stroke_color_conf = config.get('subtitle_stroke_color') or config.get('subtitleStrokeColor')
            subtitle_stroke_width_conf = config.get('subtitle_stroke_width') or config.get('subtitleStrokeWidth')

            options: Dict[str, Any] = {
                # 仅当生成了有效的字幕文件且开启了自动字幕时才启用字幕
                'subtitle_enabled': bool(subtitle_path) and bool(config.get('auto_subtitle', True)),
                'keep_original_audio': False,
                # 原创解说默认使用更醒目的“大号字幕”样式，如前端选择则按选择覆盖
                'subtitle_style': subtitle_style_name or 'large',
            }

            # 允许前端覆盖字幕位置
            if subtitle_position_conf:
                options['subtitle_position'] = str(subtitle_position_conf)

            # 允许前端覆盖字幕字体大小（数值合法时生效）
            try:
                if subtitle_font_size_conf is not None:
                    fs_val = int(float(subtitle_font_size_conf))
                    if fs_val > 0:
                        options['subtitle_font_size'] = fs_val
            except Exception:
                pass

            # 高级字幕样式覆盖：字体 / 颜色 / 描边 / 背景
            if subtitle_font_conf:
                try:
                    options['subtitle_font'] = str(subtitle_font_conf)
                except Exception:
                    pass

            if subtitle_color_conf:
                try:
                    options['subtitle_color'] = str(subtitle_color_conf)
                except Exception:
                    pass

            if subtitle_bg_color_conf:
                try:
                    options['subtitle_bg_color'] = str(subtitle_bg_color_conf)
                except Exception:
                    pass

            if subtitle_stroke_color_conf:
                try:
                    options['stroke_color'] = str(subtitle_stroke_color_conf)
                except Exception:
                    pass

            try:
                if subtitle_stroke_width_conf is not None:
                    sw_val = int(float(subtitle_stroke_width_conf))
                    if sw_val >= 0:
                        options['stroke_width'] = sw_val
            except Exception:
                pass

            # 若存在合法目标时长，则传递给合成器在加载后裁剪视频长度
            if max_duration_for_merge is not None and max_duration_for_merge > 0:
                options['max_duration'] = float(max_duration_for_merge)

            # 从 config 中读取音量控制参数
            voice_volume_conf = config.get('voice_volume')
            bgm_volume_conf = config.get('bgm_volume')
            original_volume_conf = config.get('original_audio_volume')
            
            if voice_volume_conf is not None:
                try:
                    options['voice_volume'] = float(voice_volume_conf)
                except Exception:
                    pass
            
            if bgm_volume_conf is not None:
                try:
                    options['bgm_volume'] = float(bgm_volume_conf)
                except Exception:
                    pass
            
            if original_volume_conf is not None:
                try:
                    options['original_audio_volume'] = float(original_volume_conf)
                except Exception:
                    pass

            composer = VideoComposer()
            composed_path = composer.merge_materials(
                video_path=clipped_video_path,  # 使用裁剪后的视频路径
                audio_path=str(audio_path_obj),
                output_path=str(output_file),
                subtitle_path=subtitle_path,
                bgm_path=bgm_path,
                options=options,
            )

            try:
                rel_path = Path(composed_path).resolve().relative_to(base_dir)
                rel_str = str(rel_path).replace('\\', '/')
            except Exception:
                rel_str = str(output_file).replace('\\', '/')

            logger.info(f'✅ 视频合成完成: {rel_str}')

            return rel_str
            
        except Exception as e:
            logger.error(f'❌ 视频合成失败: {e}')
            return None
    
    def _map_voice_clone_id(self, voice_id: str) -> str:
        """将前端的 clone-* / 自定义 ID 映射为 Voice Clone 引擎内置音色 ID。"""
        try:
            v = (voice_id or '').strip().lower()
        except Exception:
            v = ''

        if v in ('clone-zh', 'clone-zh-female', 'cn'):
            return 'zh'
        if v in ('clone-en-us', 'us'):
            return 'en-us'
        if v in ('clone-en-gb', 'gb'):
            # 后端使用 en-br 代表英式英语
            return 'en-br'
        if v in ('clone-en-au', 'au'):
            return 'en-au'
        if v in ('clone-en-in', 'in'):
            return 'en-india'
        if v in ('clone-es', 'es'):
            return 'es'
        if v in ('clone-fr', 'fr'):
            return 'fr'
        if v in ('clone-jp', 'jp'):
            return 'jp'
        if v in ('clone-kr', 'kr'):
            return 'kr'
        if v in ('clone-de', 'de'):
            # 暂无独立德语模型，退回默认英语
            return 'en-default'

        # 若本身就是内置ID（en-* / es / fr / jp / kr / zh），直接透传
        import re
        if re.match(r'^(en-(au|br|default|india|newest|us)|es|fr|jp|kr|zh)$', v):
            return v

        # 其它情况统一退回中文模型，避免直接报错
        return 'zh'
    
    def _simple_video_analysis(self, video_path: str) -> Dict:
        """简化的视频分析（备用方案）

        不再返回与真实视频无关的固定结果，而是基于视频元数据构建粗略的场景信息，
        保证在视觉引擎不可用时仍然能提供与时长相符的分析结构。
        """
        duration = 60.0
        width = None
        height = None

        try:
            vp = VideoProcessor()
            info = vp.get_video_info(video_path) or {}
            duration = float(info.get('duration') or duration)
            if duration <= 0:
                duration = 60.0
            try:
                width = int(info.get('width')) if info.get('width') is not None else None
                height = int(info.get('height')) if info.get('height') is not None else None
            except Exception:
                width = height = None
        except Exception as e:
            logger.warning(f'⚠️ 简化视频分析获取元数据失败，将使用默认时长: {e}')

        # 按时长平均分段，生成基础场景
        duration = max(1.0, duration)
        segment_count = max(1, min(6, int(duration // 10) or 1))
        seg_dur = duration / segment_count

        scenes = []
        descriptions = []
        for i in range(segment_count):
            start = i * seg_dur
            end = duration if i == segment_count - 1 else (i + 1) * seg_dur
            scenes.append({
                'id': i,
                'start_time': float(start),
                'end_time': float(end),
                'duration': float(end - start)
            })
            descriptions.append({
                'timestamp': float((start + end) / 2.0),
                'description': f'第{i+1}段画面'
            })

        summary = '原创解说视频'
        if scenes:
            summary = f"约 {int(duration)} 秒的原创解说视频，大致划分为 {len(scenes)} 个场景。"

        result: Dict[str, Any] = {
            'scenes': scenes,
            'keyframes': [],
            'descriptions': descriptions,
            'emotions': [],
            'summary': summary,
            'duration': duration
        }
        if width and height:
            result['resolution'] = f'{width}x{height}'

        return result
    
    def _template_script(self, vision_results: Dict) -> Dict:
        """规则文案（备用方案）

        当 ScriptGenerator 不可用时，根据视频分析结果动态生成一个结构化的解说文案，
        输出结构与主流程保持一致：包含 opening / segments / closing 字段，
        且每个片段的起止时间与场景时长匹配。
        """
        # 推断总时长
        duration = 0.0
        try:
            if 'duration' in vision_results:
                duration = float(vision_results.get('duration') or 0.0)
        except Exception:
            duration = 0.0

        scenes = vision_results.get('scenes') or []
        if not scenes and duration <= 0:
            # 如果没有场景信息与时长，则退回到一个约30秒的视频假设
            duration = 30.0
            segment_count = 3
            seg_dur = duration / segment_count
            scenes = []
            for i in range(segment_count):
                start = i * seg_dur
                end = duration if i == segment_count - 1 else (i + 1) * seg_dur
                scenes.append({
                    'id': i,
                    'start_time': float(start),
                    'end_time': float(end),
                    'duration': float(end - start)
                })
        elif not scenes:
            # 只有时长，按时长均分生成场景
            duration = max(duration, 1.0)
            segment_count = max(3, min(6, int(duration // 6) or 3))
            seg_dur = duration / segment_count
            scenes = []
            for i in range(segment_count):
                start = i * seg_dur
                end = duration if i == segment_count - 1 else (i + 1) * seg_dur
                scenes.append({
                    'id': i,
                    'start_time': float(start),
                    'end_time': float(end),
                    'duration': float(end - start)
                })

        # 如果时长仍未知，则根据最后一个场景推断
        if duration <= 0 and scenes:
            try:
                duration = float(scenes[-1].get('end_time') or 0.0)
            except Exception:
                duration = 0.0

        # 基于场景构造 segments
        segments = []
        for idx, scene in enumerate(scenes):
            try:
                start = float(scene.get('start_time', 0.0))
                end = float(scene.get('end_time', start))
            except Exception:
                start, end = 0.0, 0.0
            text = f"第{idx+1}段：这里展示的是视频的精彩画面片段，创作者可以在此处补充更具体的讲解内容。"
            segments.append({
                'scene_id': scene.get('id', idx),
                'start_time': start,
                'end_time': end,
                'text': text,
                'emotion': 'neutral'
            })

        summary = vision_results.get('summary') or '原创解说视频'
        opening = f"欢迎观看本期原创解说视频。{summary}"
        closing = "本期解说就到这里，感谢您的观看，我们下期再见。"

        return {
            'title': '原创解说文稿',
            'opening': opening,
            'segments': segments,
            'closing': closing
        }
    
    def _emit_progress(self, task_id: str, progress: int, message: str):
        """发送进度更新"""
        try:
            if self.socketio:
                self.socketio.emit('task_progress', {
                    'task_id': task_id,
                    'progress': progress,
                    'message': message
                })
            
            # 更新任务进度（数据库）
            try:
                self.db_manager.update_task_progress(task_id, progress)
            except Exception:
                pass
            
            logger.info(f'📊 进度: {progress}% - {message}')
            
        except Exception as e:
            logger.error(f'❌ 发送进度失败: {e}')
    
    def get_project_result(self, project_id: str) -> Dict:
        """获取项目结果"""
        try:
            project = self.db_manager.get_project(project_id)
            
            if not project:
                return {'code': 1, 'msg': '项目不存在', 'data': None}
            
            raw_result = project.get('result')
            result: Dict[str, Any]
            if isinstance(raw_result, str):
                try:
                    result = json.loads(raw_result) or {}
                except Exception:
                    result = {}
            elif isinstance(raw_result, dict):
                result = raw_result
            else:
                result = {}

            return {
                'code': 0,
                'msg': '获取成功',
                'data': {
                    'project': project,
                    'result': result
                }
            }
            
        except Exception as e:
            logger.error(f'❌ 获取结果失败: {e}')
            return {'code': 1, 'msg': f'获取失败: {str(e)}', 'data': None}
