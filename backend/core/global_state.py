"""
全局状态管理器
确保所有功能模块共享配置和状态
"""

import logging
import threading
from typing import Dict, Any, Optional, Callable
import json

logger = logging.getLogger('AIJian')


class GlobalStateManager:
    """全局状态管理器 - 单例模式"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.logger = logger
            
            # 配置管理器
            self.config_manager = None
            
            # AI引擎实例
            self.vision_analyzer = None
            self.script_generator = None
            self.sync_engine = None
            self.tts_engine = None
            self.beat_remix_engine = None
            self.multi_model_manager = None
            
            # 当前活动的模型
            self.active_llm_model = None
            self.active_vision_model = None
            self.active_tts_voice = None
            
            # 项目状态
            self.current_projects = {}
            
            # 任务队列
            self.task_queue = []
            
            # 事件监听器
            self.event_listeners = {}
            
            # 初始化
            self._init_components()
            
            logger.info('✅ 全局状态管理器初始化完成')
    
    def _init_components(self):
        """初始化所有组件"""
        try:
            # 加载配置管理器
            from backend.config.ai_config import get_config_manager
            self.config_manager = get_config_manager()
            
            # 设置活动模型
            if self.config_manager:
                self.active_llm_model = self.config_manager.llm_config.default_model
                self.active_vision_model = self.config_manager.vision_config.default_model
            
            logger.info('✅ 全局组件初始化完成')
            
        except Exception as e:
            logger.error(f'❌ 全局组件初始化失败: {e}')
    
    def get_vision_analyzer(self):
        """获取视觉分析器（单例）"""
        if self.vision_analyzer is None:
            try:
                from backend.engine.vision_analyzer import get_vision_analyzer
                self.vision_analyzer = get_vision_analyzer()
                logger.info('✅ 视觉分析器已加载')
            except Exception as e:
                logger.error(f'❌ 视觉分析器加载失败: {e}')
        return self.vision_analyzer
    
    def get_script_generator(self):
        """获取文案生成器（单例）"""
        if self.script_generator is None:
            try:
                from backend.engine.script_generator import ScriptGenerator
                # 使用当前配置的API密钥和模型参数
                api_key = None
                model_name = "gpt-4"
                base_url = None

                if self.config_manager:
                    api_key = self.config_manager.get_llm_api_key(self.active_llm_model)

                    # 根据当前活动模型选择底层模型名称和Base URL
                    if self.active_llm_model == 'openai':
                        base_url = getattr(self.config_manager.llm_config, 'custom_base_url', None)
                        model_name = getattr(self.config_manager.llm_config, 'custom_model', model_name)
                    elif self.active_llm_model == 'deepseek':
                        # DeepSeek 使用 OpenAI 兼容接口
                        base_url = "https://api.deepseek.com"
                        model_name = getattr(self.config_manager.llm_config, 'deepseek_model', 'deepseek-chat')

                self.script_generator = ScriptGenerator(
                    api_key=api_key,
                    model=model_name,
                    base_url=base_url
                )
                logger.info(f'✅ 文案生成器已加载（LLM模型: {self.active_llm_model}, 底层模型: {model_name}）')
            except Exception as e:
                logger.error(f'❌ 文案生成器加载失败: {e}')
        return self.script_generator
    
    def get_sync_engine(self):
        """获取同步引擎（单例）"""
        if self.sync_engine is None:
            try:
                from backend.engine.sync_engine import get_sync_engine
                self.sync_engine = get_sync_engine()
                logger.info('✅ 同步引擎已加载')
            except Exception as e:
                logger.error(f'❌ 同步引擎加载失败: {e}')
        return self.sync_engine
    
    def get_tts_engine(self):
        """获取TTS引擎（单例）"""
        if self.tts_engine is None:
            try:
                from backend.engine.tts_engine import TTSEngine
                self.tts_engine = TTSEngine()
                logger.info('✅ TTS引擎已加载')
            except Exception as e:
                logger.error(f'❌ TTS引擎加载失败: {e}')
        return self.tts_engine
    
    def get_beat_remix_engine(self):
        """获取混剪引擎（单例）"""
        if self.beat_remix_engine is None:
            try:
                from backend.engine.beat_remix_engine import get_beat_remix_engine
                self.beat_remix_engine = get_beat_remix_engine()
                logger.info('✅ 混剪引擎已加载')
            except Exception as e:
                logger.error(f'❌ 混剪引擎加载失败: {e}')
        return self.beat_remix_engine
    
    def get_multi_model_manager(self):
        """获取多模型管理器（单例）"""
        if self.multi_model_manager is None:
            try:
                from backend.engine.multi_model_adapter import get_multi_model_manager
                self.multi_model_manager = get_multi_model_manager()
                logger.info('✅ 多模型管理器已加载')
            except Exception as e:
                logger.error(f'❌ 多模型管理器加载失败: {e}')
        return self.multi_model_manager
    
    def reload_config(self):
        """重新加载配置（当用户保存设置时调用）"""
        try:
            logger.info('🔄 重新加载配置...')
            
            # 重新加载配置管理器
            if self.config_manager:
                self.config_manager.load_config()
                self.config_manager.load_censor_words()
            
            # 更新活动模型
            if self.config_manager:
                old_llm = self.active_llm_model
                old_vision = self.active_vision_model
                
                self.active_llm_model = self.config_manager.llm_config.default_model
                self.active_vision_model = self.config_manager.vision_config.default_model
                
                # 如果模型改变，重置相关引擎
                if old_llm != self.active_llm_model:
                    logger.info(f'🔄 LLM模型切换: {old_llm} → {self.active_llm_model}')
                    self.script_generator = None  # 重置以使用新模型
                
                if old_vision != self.active_vision_model:
                    logger.info(f'🔄 视觉模型切换: {old_vision} → {self.active_vision_model}')
            
            # 触发配置更新事件
            self.emit_event('config_updated', {
                'llm_model': self.active_llm_model,
                'vision_model': self.active_vision_model
            })
            
            logger.info('✅ 配置重新加载完成')
            return True
            
        except Exception as e:
            logger.error(f'❌ 配置重新加载失败: {e}')
            return False
    
    def set_active_llm_model(self, model_name: str):
        """设置活动的LLM模型"""
        if self.active_llm_model != model_name:
            logger.info(f'🔄 切换LLM模型: {self.active_llm_model} → {model_name}')
            self.active_llm_model = model_name
            self.script_generator = None  # 重置以使用新模型
            
            # 更新配置
            if self.config_manager:
                self.config_manager.llm_config.default_model = model_name
                self.config_manager.save_config()
            
            self.emit_event('llm_model_changed', {'model': model_name})
    
    def set_active_vision_model(self, model_name: str):
        """设置活动的视觉模型"""
        if self.active_vision_model != model_name:
            logger.info(f'🔄 切换视觉模型: {self.active_vision_model} → {model_name}')
            self.active_vision_model = model_name
            
            # 更新配置
            if self.config_manager:
                self.config_manager.vision_config.default_model = model_name
                self.config_manager.save_config()
            
            self.emit_event('vision_model_changed', {'model': model_name})
    
    def get_project_state(self, project_id: str) -> Optional[Dict]:
        """获取项目状态"""
        return self.current_projects.get(project_id)
    
    def set_project_state(self, project_id: str, state: Dict):
        """设置项目状态"""
        self.current_projects[project_id] = state
        self.emit_event('project_state_changed', {
            'project_id': project_id,
            'state': state
        })
    
    def remove_project_state(self, project_id: str):
        """移除项目状态"""
        if project_id in self.current_projects:
            del self.current_projects[project_id]
            self.emit_event('project_removed', {'project_id': project_id})
    
    def add_event_listener(self, event_name: str, callback: Callable):
        """添加事件监听器"""
        if event_name not in self.event_listeners:
            self.event_listeners[event_name] = []
        self.event_listeners[event_name].append(callback)
        logger.info(f'✅ 添加事件监听器: {event_name}')
    
    def remove_event_listener(self, event_name: str, callback: Callable):
        """移除事件监听器"""
        if event_name in self.event_listeners:
            self.event_listeners[event_name].remove(callback)
    
    def emit_event(self, event_name: str, data: Any):
        """触发事件"""
        if event_name in self.event_listeners:
            for callback in self.event_listeners[event_name]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f'❌ 事件回调执行失败 ({event_name}): {e}')
    
    def get_available_models(self) -> Dict[str, list]:
        """获取所有可用的模型"""
        available = {
            'llm': [],
            'vision': []
        }
        
        if not self.config_manager:
            return available
        
        # 检查LLM模型（含新旧字段兼容）
        llm_models = [
            ('tongyi', '通义千问', (self.config_manager.llm_config.qwen_api_key or self.config_manager.llm_config.tongyi_api_key)),
            ('wenxin', '文心一言', (self.config_manager.llm_config.ernie_api_key or self.config_manager.llm_config.wenxin_api_key)),
            ('chatglm', 'ChatGLM', self.config_manager.llm_config.chatglm_api_key),
            ('deepseek', 'DeepSeek', self.config_manager.llm_config.deepseek_api_key),
            ('openai', 'OpenAI', self.config_manager.llm_config.custom_api_key),
            ('claude', 'Claude', (self.config_manager.llm_config.anthropic_api_key or self.config_manager.llm_config.claude_api_key)),
            ('gemini', 'Gemini', self.config_manager.llm_config.gemini_api_key),
        ]
        
        for model_id, model_name, api_key in llm_models:
            available['llm'].append({
                'id': model_id,
                'name': model_name,
                'available': bool(api_key),
                'active': model_id == self.active_llm_model
            })
        
        # 检查视觉模型（含新旧字段兼容）
        vision_models = [
            ('qianwen_vl', '通义千问VL', (self.config_manager.vision_config.qwen_vl_api_key or self.config_manager.vision_config.tongyi_vl_api_key)),
            ('baidu', '百度视觉', self.config_manager.vision_config.baidu_vision_api_key),
            ('gemini', 'Gemini Vision', self.config_manager.vision_config.gemini_vision_api_key),
            ('openai', 'GPT-4 Vision', (self.config_manager.vision_config.gpt4v_api_key or self.config_manager.vision_config.openai_vision_api_key)),
        ]
        
        for model_id, model_name, api_key in vision_models:
            available['vision'].append({
                'id': model_id,
                'name': model_name,
                'available': bool(api_key),
                'active': model_id == self.active_vision_model
            })
        
        return available
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        return {
            'config_loaded': self.config_manager is not None,
            'active_llm_model': self.active_llm_model,
            'active_vision_model': self.active_vision_model,
            'engines_loaded': {
                'vision_analyzer': self.vision_analyzer is not None,
                'script_generator': self.script_generator is not None,
                'sync_engine': self.sync_engine is not None,
                'tts_engine': self.tts_engine is not None,
                'beat_remix_engine': self.beat_remix_engine is not None,
                'multi_model_manager': self.multi_model_manager is not None,
            },
            'active_projects': len(self.current_projects),
            'available_models': self.get_available_models()
        }


# 全局实例
_global_state = None


def get_global_state() -> GlobalStateManager:
    """获取全局状态管理器单例"""
    global _global_state
    if _global_state is None:
        _global_state = GlobalStateManager()
    return _global_state
