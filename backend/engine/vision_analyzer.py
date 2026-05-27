"""
视频画面分析引擎
使用视觉大模型分析视频内容
"""

import cv2
import numpy as np
from PIL import Image
import logging
from typing import List, Dict, Any
import os

logger = logging.getLogger('AIJian')


class VisionAnalyzer:
    """视频画面分析引擎"""
    
    def __init__(self):
        """初始化视觉分析器"""
        self.logger = logger
        self.models_loaded = False
        self._load_models()
    
    def _load_clip(self):
        """加载CLIP模型"""
        try:
            import clip
            import torch
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.clip_model, self.clip_preprocess = clip.load("ViT-B/32", device=device)
            self.clip_available = True
            self.logger.info('✅ CLIP模型加载成功')
        except ImportError:
            # CLIP未安装，使用备用方案
            self.logger.info('ℹ️ CLIP模型未安装，将使用备用图像分析方案')
            self.clip_available = False
            self.clip_model = None
            self.clip_preprocess = None
        except Exception as e:
            self.logger.warning(f'⚠️ CLIP模型加载失败: {e}')
            self.clip_available = False
            self.clip_model = None
            self.clip_preprocess = None
    
    def _load_models(self):
        """加载AI模型（延迟加载）"""
        try:
            # 尝试加载CLIP模型
            self._load_clip()
            
            # 尝试加载YOLO模型
            try:
                from ultralytics import YOLO
                self.yolo_model = YOLO('yolov8n.pt')
                self.yolo_available = True
                self.logger.info("✅ YOLO模型加载成功")
            except Exception as e:
                self.yolo_available = False
                self.yolo_model = None
                self.logger.warning(f"⚠️ YOLO模型加载失败: {e}")
            
            self.models_loaded = True
            
        except Exception as e:
            self.logger.error(f"❌ 模型加载失败: {e}")
            self.models_loaded = False
    
    def analyze_video(self, video_path: str, max_keyframes: int = 10) -> Dict[str, Any]:
        """
        完整分析视频
        
        Args:
            video_path: 视频文件路径
            max_keyframes: 最大关键帧数量
            
        Returns:
            分析结果字典
        """
        self.logger.info(f"🎬 开始分析视频: {video_path}")
        
        results = {
            'video_path': video_path,
            'keyframes': [],
            'scenes': [],
            'objects': [],
            'descriptions': [],
            'emotions': [],
            'summary': ''
        }
        
        try:
            # 1. 场景检测
            scenes = self.detect_scenes(video_path)
            results['scenes'] = scenes
            self.logger.info(f"✅ 检测到 {len(scenes)} 个场景")
            
            # 2. 提取关键帧
            keyframes = self.extract_keyframes(video_path, scenes, max_keyframes)
            results['keyframes'] = keyframes
            self.logger.info(f"✅ 提取了 {len(keyframes)} 个关键帧")
            
            # 3. 分析每个关键帧
            for i, frame_info in enumerate(keyframes):
                frame = frame_info['image']
                timestamp = frame_info['timestamp']
                
                # 物体检测
                if self.yolo_available:
                    objects = self.detect_objects(frame)
                    results['objects'].append({
                        'timestamp': timestamp,
                        'objects': objects
                    })
                
                # 生成描述
                description = self.generate_description(frame, timestamp)
                results['descriptions'].append({
                    'timestamp': timestamp,
                    'description': description
                })
                
                # 情感分析
                emotion = self.analyze_emotion(frame)
                results['emotions'].append({
                    'timestamp': timestamp,
                    'emotion': emotion
                })
                
                self.logger.info(f"✅ 分析关键帧 {i+1}/{len(keyframes)}")
            
            # 4. 生成视频摘要
            results['summary'] = self.generate_summary(results)
            
            self.logger.info("✅ 视频分析完成")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 视频分析失败: {e}", exc_info=True)
            return results
    
    def detect_scenes(self, video_path: str, threshold: float = 30.0) -> List[Dict[str, Any]]:
        """
        场景检测
        
        Args:
            video_path: 视频路径
            threshold: 场景切换阈值
            
        Returns:
            场景列表
        """
        scenes = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            self.logger.error(f"❌ 无法打开视频: {video_path}")
            return scenes
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        prev_frame = None
        scene_start = 0
        scene_id = 0
        
        for frame_num in range(0, total_frames, int(fps)):  # 每秒采样一次
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            
            if not ret:
                break
            
            if prev_frame is not None:
                # 计算帧差异
                diff = cv2.absdiff(prev_frame, frame)
                diff_score = np.mean(diff)
                
                # 场景切换检测
                if diff_score > threshold:
                    scene_end = frame_num / fps
                    scenes.append({
                        'id': scene_id,
                        'start_time': scene_start,
                        'end_time': scene_end,
                        'duration': scene_end - scene_start
                    })
                    scene_start = scene_end
                    scene_id += 1
            
            prev_frame = frame
        
        # 添加最后一个场景
        if scene_start < total_frames / fps:
            scenes.append({
                'id': scene_id,
                'start_time': scene_start,
                'end_time': total_frames / fps,
                'duration': (total_frames / fps) - scene_start
            })
        
        cap.release()
        return scenes
    
    def extract_keyframes(self, video_path: str, scenes: List[Dict], 
                         max_frames: int = 10) -> List[Dict[str, Any]]:
        """
        提取关键帧
        
        Args:
            video_path: 视频路径
            scenes: 场景列表
            max_frames: 最大帧数
            
        Returns:
            关键帧列表
        """
        keyframes = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return keyframes
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # 如果没有场景，创建一个默认场景
        if not scenes:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            scenes = [{
                'id': 0,
                'start_time': 0,
                'end_time': total_frames / fps,
                'duration': total_frames / fps
            }]
        
        # 计算每个场景应该提取多少帧
        frames_per_scene = max(1, max_frames // len(scenes))
        
        for scene in scenes:
            start_frame = int(scene['start_time'] * fps)
            end_frame = int(scene['end_time'] * fps)
            duration = end_frame - start_frame
            
            if duration <= 0:
                continue
            
            # 均匀采样
            step = max(1, duration // (frames_per_scene + 1))
            
            for i in range(1, frames_per_scene + 1):
                frame_num = start_frame + i * step
                if frame_num >= end_frame:
                    break
                
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if ret:
                    keyframes.append({
                        'timestamp': frame_num / fps,
                        'frame_number': frame_num,
                        'image': frame,
                        'scene_id': scene['id']
                    })
        
        cap.release()
        return keyframes
    
    def detect_objects(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        检测图像中的物体
        
        Args:
            image: 图像数组
            
        Returns:
            物体列表
        """
        if not self.yolo_available:
            return []
        
        try:
            results = self.yolo_model(image, verbose=False)
            objects = []
            
            for r in results:
                for box in r.boxes:
                    objects.append({
                        'class': r.names[int(box.cls)],
                        'confidence': float(box.conf),
                        'bbox': box.xyxy[0].tolist()
                    })
            
            return objects
            
        except Exception as e:
            self.logger.error(f"❌ 物体检测失败: {e}")
            return []
    
    def generate_description(self, image: np.ndarray, timestamp: float) -> str:
        """
        生成图像描述
        
        Args:
            image: 图像数组
            timestamp: 时间戳
            
        Returns:
            描述文本
        """
        if self.clip_available:
            try:
                import torch
                import clip
                
                # 转换图像
                image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                image_input = self.clip_preprocess(image_pil).unsqueeze(0)
                
                # 预定义的描述候选
                text_candidates = [
                    "人物特写镜头",
                    "人物在说话",
                    "人物在行走",
                    "室内场景",
                    "室外场景",
                    "风景画面",
                    "动作场景",
                    "静态画面",
                    "明亮的场景",
                    "昏暗的场景"
                ]
                
                text_tokens = clip.tokenize(text_candidates)
                
                with torch.no_grad():
                    image_features = self.clip_model.encode_image(image_input)
                    text_features = self.clip_model.encode_text(text_tokens)
                    
                    # 计算相似度
                    similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
                    values, indices = similarity[0].topk(1)
                
                return text_candidates[indices[0]]
                
            except Exception as e:
                self.logger.error(f"❌ CLIP描述生成失败: {e}")
        
        # 备用方案：基于图像特征的简单描述
        return self._generate_simple_description(image)
    
    def _generate_simple_description(self, image: np.ndarray) -> str:
        """生成简单描述（备用方案）"""
        # 分析图像亮度
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        
        # 分析颜色
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        saturation = np.mean(hsv[:, :, 1])
        
        if brightness > 150:
            desc = "明亮的画面"
        elif brightness < 80:
            desc = "昏暗的画面"
        else:
            desc = "正常光线的画面"
        
        if saturation > 100:
            desc += "，色彩鲜艳"
        
        return desc
    
    def analyze_emotion(self, image: np.ndarray) -> str:
        """
        分析画面情感
        
        Args:
            image: 图像数组
            
        Returns:
            情感标签
        """
        # 基于颜色和亮度的简单情感分析
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        avg_brightness = hsv[:, :, 2].mean()
        avg_saturation = hsv[:, :, 1].mean()
        avg_hue = hsv[:, :, 0].mean()
        
        # 情感判断
        if avg_brightness > 150 and avg_saturation > 100:
            return "happy"  # 明亮且鲜艳 = 快乐
        elif avg_brightness < 100:
            return "sad"  # 昏暗 = 悲伤
        elif avg_saturation > 150:
            return "excited"  # 高饱和度 = 兴奋
        elif avg_hue < 30 or avg_hue > 150:
            return "warm"  # 暖色调 = 温暖
        else:
            return "neutral"  # 中性
    
    def generate_summary(self, analysis_results: Dict[str, Any]) -> str:
        """
        生成视频摘要
        
        Args:
            analysis_results: 分析结果
            
        Returns:
            摘要文本
        """
        scenes_count = len(analysis_results['scenes'])
        keyframes_count = len(analysis_results['keyframes'])
        
        # 统计主要情感
        emotions = [e['emotion'] for e in analysis_results['emotions']]
        main_emotion = max(set(emotions), key=emotions.count) if emotions else 'neutral'
        
        # 统计主要物体
        all_objects = []
        for obj_info in analysis_results['objects']:
            all_objects.extend([o['class'] for o in obj_info['objects']])
        
        main_objects = []
        if all_objects:
            from collections import Counter
            object_counts = Counter(all_objects)
            main_objects = [obj for obj, count in object_counts.most_common(3)]
        
        summary = f"视频包含{scenes_count}个场景，"
        summary += f"提取了{keyframes_count}个关键帧。"
        summary += f"整体氛围偏向{main_emotion}。"
        
        if main_objects:
            summary += f"主要内容包含：{', '.join(main_objects)}。"
        
        return summary


# 单例模式
_vision_analyzer_instance = None


def get_vision_analyzer():
    """获取视觉分析器单例"""
    global _vision_analyzer_instance
    if _vision_analyzer_instance is None:
        _vision_analyzer_instance = VisionAnalyzer()
    return _vision_analyzer_instance
