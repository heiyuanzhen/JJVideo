"""
解说文案生成引擎
使用大语言模型根据画面分析生成解说文案
支持黄金三秒开头、十大爆款钩子等NarratoAI技巧
"""

import json
import logging
import sys
import os
from typing import Dict, List, Any, Optional

# 添加prompts模块到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from prompts.narration_prompts import NarrationPrompts, generate_narration_prompt

logger = logging.getLogger('AIJian')


class ScriptGenerator:
    """解说文案生成引擎"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4", base_url: Optional[str] = None):
        """
        初始化文案生成器
        
        Args:
            api_key: OpenAI API密钥（可选）
            model: 模型名称
            base_url: OpenAI兼容后端的基础URL（可选）
        """
        self.logger = logger
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = None
        
        if api_key:
            self._init_openai_client()
    
    def _init_openai_client(self):
        """初始化OpenAI客户端"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url or "https://api.openai.com/v1"
            )
            self.logger.info("✅ OpenAI客户端初始化成功")
        except Exception as e:
            self.logger.warning(f"⚠️ OpenAI客户端初始化失败: {e}")
            self.client = None
    
    def generate_script(self, vision_analysis: Dict[str, Any], 
                       style: str = 'professional',
                       duration: Optional[float] = None,
                       narration_mode: str = 'general',
                       custom_prompt: Optional[str] = None,
                       hook_type: str = 'suspense',
                       use_viral_prompts: bool = True) -> Dict[str, Any]:
        """
        生成解说文案
        
        Args:
            vision_analysis: 视觉分析结果
            style: 文案风格 (professional/casual/humorous/dramatic)
            duration: 目标时长（秒）
            narration_mode: 解说类型（例如 general/film_1st/film_3rd/animation_3rd/documentary/romance/suspense_twist）
            custom_prompt: 自定义提示词
            hook_type: 开头钩子类型 (suspense/reversal/numbers/pain_point等)
            use_viral_prompts: 是否使用病毒式传播提示词（黄金三秒法则等）
            
        Returns:
            生成的文案
        """
        hook_name = NarrationPrompts.HOOK_TYPES.get(hook_type, {}).get('name', hook_type)
        self.logger.info(f"📝 开始生成{style}风格解说文案，开头钩子：{hook_name}")
        
        try:
            # 1. 构建提示词
            if use_viral_prompts:
                # 使用NarratoAI病毒式传播提示词
                prompt = self._build_viral_prompt(vision_analysis, hook_type, custom_prompt, narration_mode)
            else:
                # 使用传统提示词
                prompt = self._build_prompt(vision_analysis, style, duration, custom_prompt)
            
            # 2. 调用LLM生成
            if self.client:
                script_json = self._call_openai(prompt)
            else:
                # 使用备用方案
                script_json = self._generate_fallback(vision_analysis, style)
            
            # 3. 解析结果
            script = self._parse_script(script_json)
            
            # 4. 时间轴对齐
            aligned_script = self._align_with_timeline(script, vision_analysis)
            
            # 5. 优化文案（传入目标时长用于强制字数控制）
            optimized_script = self._optimize_script(aligned_script, target_duration=duration)
            
            self.logger.info("✅ 文案生成完成")
            return optimized_script
            
        except Exception as e:
            self.logger.error(f"❌ 文案生成失败: {e}", exc_info=True)
            fallback_json = self._generate_fallback(vision_analysis, style)
            return self._parse_script(fallback_json)
    
    def _build_viral_prompt(self, vision_analysis: Dict[str, Any],
                           hook_type: str,
                           custom_prompt: Optional[str] = None,
                           narration_mode: str = 'general') -> str:
        """
        构建病毒式传播提示词（基于NarratoAI）
        
        Args:
            vision_analysis: 视觉分析结果
            hook_type: 开头钩子类型
            custom_prompt: 自定义要求
        
        Returns:
            完整提示词
        """
        # 将视觉分析转换为Markdown格式
        video_description = self._convert_analysis_to_markdown(vision_analysis)
        
        # 使用NarratoAI提示词生成器
        prompt = generate_narration_prompt(
            video_description=video_description,
            hook_type=hook_type,
            custom_requirements=custom_prompt,
            narration_mode=narration_mode
        )
        
        return prompt
    
    def _convert_analysis_to_markdown(self, vision_analysis: Dict[str, Any]) -> str:
        """将视觉分析结果转换为Markdown格式"""
        markdown = "# 视频内容分析\n\n"

        scenes = vision_analysis.get('scenes', [])
        descriptions = vision_analysis.get('descriptions', [])
        emotions = vision_analysis.get('emotions', [])
        objects_list = vision_analysis.get('objects', [])

        for i, scene in enumerate(scenes):
            markdown += f"## 片段 {i+1}\n"
            markdown += f"- 时间范围：{scene.get('start_time', 0):.1f}s-{scene.get('end_time', 0):.1f}s\n"

            desc_item = descriptions[i] if i < len(descriptions) else {}
            # 优先使用多模型增强后的描述，其次退回基础描述
            desc_text = desc_item.get('enhanced_description') or desc_item.get('description') or '画面内容'
            markdown += f"- 片段描述：{desc_text}\n"

            emotion_item = emotions[i] if i < len(emotions) else {}
            emotion = emotion_item.get('emotion') or emotion_item.get('mood')
            if emotion:
                markdown += f"- 情绪氛围：{emotion}\n"

            markdown += "\n"

        return markdown
    
    def _build_prompt(self, vision_analysis: Dict[str, Any], 
                     style: str, duration: Optional[float],
                     custom_prompt: Optional[str]) -> str:
        """构建传统提示词"""
        # 整理场景信息
        scenes_info = []
        for i, scene in enumerate(vision_analysis.get('scenes', [])):
            desc_list = vision_analysis.get('descriptions', [])
            emotion_list = vision_analysis.get('emotions', [])
            obj_list = vision_analysis.get('objects', [])
            
            scene_desc = desc_list[i] if i < len(desc_list) else {}
            scene_emotion = emotion_list[i] if i < len(emotion_list) else {}
            scene_objects = obj_list[i] if i < len(obj_list) else {}
            
            scenes_info.append({
                'scene_id': scene.get('id', i),
                'time_range': f"{scene.get('start_time', 0):.1f}s - {scene.get('end_time', 0):.1f}s",
                'duration': f"{scene.get('duration', 0):.1f}s",
                'description': scene_desc.get('description', '画面内容'),
                'emotion': scene_emotion.get('emotion', 'neutral'),
                'objects': []
            })
        
        # 风格描述
        style_descriptions = {
            'professional': '专业、正式、客观',
            'casual': '轻松、随意、亲切',
            'humorous': '幽默、风趣、有趣',
            'dramatic': '戏剧化、有张力、引人入胜',
            'educational': '教育性、知识性、详细',
            'storytelling': '故事性、叙事性、引人入胜'
        }
        
        style_desc = style_descriptions.get(style, '专业')
        
        # 计算建议字数（用于提示）
        suggested_chars = ''
        if duration and duration > 0:
            max_chars = int(duration * 3.5)  # 每秒3.5字
            suggested_chars = f'\n- **字数限制：总字数不得超过{max_chars}字**（按{duration}秒 × 3.5字/秒计算）'
        
        # 构建提示词
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = f"""你是一个专业的视频解说文案撰写专家。请根据以下视频画面分析结果，生成{style_desc}风格的解说文案。

视频信息：
- 场景数量：{len(scenes_info)}
- 视频摘要：{vision_analysis.get('summary', '精彩视频内容')}
{f'- 目标时长：{duration}秒' if duration else ''}{suggested_chars}

场景详情：
{json.dumps(scenes_info, ensure_ascii=False, indent=2)}

文案要求：
1. **【关键】必须为每个场景生成一个独立的 segment**，segments 数组的长度必须等于场景数量 {len(scenes_info)}
2. 每个 segment 的 text 必须准确描述对应场景的画面内容，不得跳过任何场景
3. 每个 segment 的 start_time 和 end_time 必须与对应场景的时间范围匹配
4. **【严格限制】所有 segments 的 text 总字数不得超过上述字数限制**，请精简表达
5. 语言风格要{style_desc}、流畅、有吸引力
6. 控制语速和节奏，确保解说时长与场景时长匹配（每秒约3-4个汉字）
7. 使用生动的描述词，增强观看体验
8. 开头要有吸引力，结尾要有总结
9. 根据画面情感调整语气（happy/sad/excited等）

请按以下JSON格式输出：
{{
    "title": "视频标题（简短有吸引力）",
    "opening": "开场白（吸引观众注意）",
    "segments": [
        {{
            "scene_id": 0,
            "start_time": 0.0,
            "end_time": 5.0,
            "text": "这一段的解说文本",
            "emotion": "neutral",
            "emphasis": ["重点词1", "重点词2"]
        }}
    ],
    "closing": "结束语（总结或呼吁）"
}}
"""
        
        return prompt
    
    def _call_openai(self, prompt: str) -> str:
        """调用OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": NarrationPrompts.SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"❌ OpenAI API调用失败: {e}")
            raise
    
    def _generate_fallback(self, vision_analysis: Dict[str, Any], style: str) -> str:
        """生成备用文案"""
        self.logger.info("📝 使用备用方案生成文案")
        
        scenes = vision_analysis.get('scenes', [])
        descriptions = vision_analysis.get('descriptions', [])
        emotions = vision_analysis.get('emotions', [])
        
        segments = []
        
        # 生成开场白
        opening = "欢迎观看本期视频，让我们一起来看看精彩的内容。"
        
        # 为每个场景生成文案
        for i, scene in enumerate(scenes):
            desc = descriptions[i].get('description', '精彩画面') if i < len(descriptions) else '精彩画面'
            emotion = emotions[i].get('emotion', 'neutral') if i < len(emotions) else 'neutral'
            
            # 根据情感调整文案
            if emotion == 'happy':
                text = f"在这个充满活力的场景中，我们可以看到{desc}，画面十分欢快。"
            elif emotion == 'sad':
                text = f"此时画面转向了{desc}，氛围变得沉静。"
            elif emotion == 'excited':
                text = f"接下来是令人兴奋的{desc}，让人眼前一亮。"
            else:
                text = f"画面中呈现的是{desc}，内容丰富多彩。"
            
            segments.append({
                'scene_id': scene.get('id', i),
                'start_time': scene.get('start_time', 0),
                'end_time': scene.get('end_time', 0),
                'text': text,
                'emotion': emotion,
                'emphasis': []
            })
        
        # 生成结束语
        closing = "以上就是本期视频的全部内容，感谢观看！"
        
        script = {
            'title': '精彩视频解说',
            'opening': opening,
            'segments': segments,
            'closing': closing
        }
        
        return json.dumps(script, ensure_ascii=False)
    
    def _parse_script(self, script_json: str) -> Dict[str, Any]:
        """解析脚本JSON"""
        try:
            script = json.loads(script_json)
            
            # 验证必需字段
            if 'segments' not in script:
                script['segments'] = []
            if 'title' not in script:
                script['title'] = '视频解说'
            if 'opening' not in script:
                script['opening'] = ''
            if 'closing' not in script:
                script['closing'] = ''
            
            return script
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ JSON解析失败: {e}")
            return {
                'title': '视频解说',
                'opening': '',
                'segments': [],
                'closing': ''
            }
    
    def _align_with_timeline(self, script: Dict[str, Any], 
                            vision_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """时间轴对齐"""
        scenes = vision_analysis.get('scenes', [])

        # 预构建 scene_id 到场景的映射，便于后续根据 scene_id 回填时间
        scene_by_id = {}
        for idx, sc in enumerate(scenes):
            sid = sc.get('id', idx)
            if sid not in scene_by_id:
                scene_by_id[sid] = sc

        segments = script.get('segments', []) or []

        for idx, segment in enumerate(segments):
            # 优先使用已有 scene_id 做映射
            seg_scene = None
            seg_sid = segment.get('scene_id')
            if seg_sid is not None and seg_sid in scene_by_id:
                seg_scene = scene_by_id[seg_sid]

            start_time = segment.get('start_time')
            end_time = segment.get('end_time')

            # 如果没有 scene_id，但有 start_time，则按时间范围映射到最近场景
            if seg_scene is None and start_time is not None:
                for sc in scenes:
                    sc_start = sc.get('start_time', 0)
                    sc_end = sc.get('end_time', float('inf'))
                    if start_time >= sc_start and start_time < sc_end:
                        seg_scene = sc
                        segment['scene_id'] = sc.get('id', idx)
                        break

            # 如果既没有 scene_id 也没有有效 start_time，则按索引兜底映射到对应场景
            if seg_scene is None and idx < len(scenes):
                seg_scene = scenes[idx]
                segment['scene_id'] = seg_scene.get('id', idx)

            # 尝试用场景时间补全 / 校正 start_time / end_time
            if seg_scene is not None:
                sc_start = float(seg_scene.get('start_time', 0.0) or 0.0)
                sc_end = float(seg_scene.get('end_time', sc_start + 5.0) or (sc_start + 5.0))

                # 没有 start_time 时，用场景起始
                if start_time is None:
                    start_time = sc_start
                # 如果 end_time 缺失或不大于 start_time，则用场景结束时间
                if end_time is None or end_time <= start_time:
                    end_time = sc_end

                segment['start_time'] = float(start_time)
                segment['end_time'] = float(end_time)

        return script
    
    def _optimize_script(self, script: Dict[str, Any], target_duration: Optional[float] = None) -> Dict[str, Any]:
        """优化文案
        
        Args:
            script: 待优化的脚本
            target_duration: 用户设定的目标时长（秒），如果提供则优先使用此值控制字数
        """
        self.logger.info(f'📝 开始优化文案，用户设定目标时长: {target_duration}秒')
        # 1. 检查文案长度
        for segment in script.get('segments', []):
            text = segment.get('text', '')
            duration = segment.get('end_time', 0) - segment.get('start_time', 0)
            
            # 估算语速（每秒约3-4个汉字）
            estimated_duration = len(text) / 3.5
            
            if estimated_duration > duration * 1.2:
                # 文案太长，需要缩短
                max_length = int(duration * 3.5)
                segment['text'] = text[:max_length] + '...'
                segment['warning'] = '文案已自动缩短以匹配时长'
        
        # 2. 添加停顿标记
        for segment in script.get('segments', []):
            text = segment.get('text', '')
            # 移除可能存在的停顿标记，保证文案干净自然
            text = text.replace('[pause:0.3]', '').replace('[pause:0.2]', '')
            segment['text'] = text
        
        # 3. 计算总时长和总字数，强制控制在目标时长内
        if script.get('segments'):
            # 优先使用用户设定的目标时长，其次使用segments的最大时间
            segments_duration = max(seg.get('end_time', 0) for seg in script['segments'])
            script['total_duration'] = segments_duration
            
            # 使用目标时长（用户设定）来控制字数，而不是segments的总时长
            control_duration = target_duration if target_duration and target_duration > 0 else segments_duration
            
            # 计算总字数
            total_chars = sum(len(seg.get('text', '')) for seg in script['segments'])
            
            self.logger.info(
                f'📊 文案统计: 总字数={total_chars}字, '
                f'segments时长={segments_duration:.1f}秒, '
                f'用户目标时长={target_duration}秒, '
                f'控制时长={control_duration:.1f}秒'
            )
            
            # 如果总字数超过目标时长的最大允许值（每秒3.5个字，不允许超标）
            if control_duration > 0:
                # 严格控制：不给容差，直接按目标时长计算最大字数
                max_allowed_chars = int(control_duration * 3.5)
                
                if total_chars > max_allowed_chars:
                    self.logger.warning(
                        f'⚠️ 【强制裁剪】文案总字数{total_chars}超过目标时长{control_duration:.1f}秒的最大值{max_allowed_chars}字，'
                        f'将强制裁剪到{max_allowed_chars}字以内'
                    )
                    
                    # 按比例裁剪每个 segment 的文本
                    scale = max_allowed_chars / total_chars
                    for segment in script['segments']:
                        text = segment.get('text', '')
                        if text:
                            target_len = int(len(text) * scale)
                            if target_len < len(text):
                                # 裁剪时尽量保留完整的句子
                                truncated = text[:target_len]
                                # 尝试在最后一个句号/逗号/问号/感叹号处截断
                                for punct in ['。', '！', '？', '，', '、']:
                                    last_punct = truncated.rfind(punct)
                                    if last_punct > target_len * 0.8:  # 如果标点在后80%位置
                                        truncated = truncated[:last_punct + 1]
                                        break
                                segment['text'] = truncated
                                segment['warning'] = f'文案已被强制裁剪（原{len(text)}字 → {len(truncated)}字）'
                    
                    # 重新计算裁剪后的总字数
                    new_total_chars = sum(len(seg.get('text', '')) for seg in script['segments'])
                    self.logger.info(f'✅ 裁剪完成：{total_chars}字 → {new_total_chars}字（目标≤{max_allowed_chars}字）')
                    
                    # 更新script的元数据
                    script['original_chars'] = total_chars
                    script['optimized_chars'] = new_total_chars
                    script['char_limit'] = max_allowed_chars
                else:
                    self.logger.info(f'✅ 文案字数{total_chars}符合目标时长{control_duration:.1f}秒的要求（≤{max_allowed_chars}字）')
                    script['original_chars'] = total_chars
                    script['optimized_chars'] = total_chars
                    script['char_limit'] = max_allowed_chars
            else:
                self.logger.warning(f'⚠️ 无法计算控制时长（target_duration={target_duration}, segments_duration={segments_duration}），跳过字数控制')
        
        return script


# 单例模式
_script_generator_instance = None


def get_script_generator(api_key: Optional[str] = None):
    """获取文案生成器单例"""
    global _script_generator_instance
    if _script_generator_instance is None:
        _script_generator_instance = ScriptGenerator(api_key=api_key)
    return _script_generator_instance
