"""
多模型适配器
支持通义千问、文心一言、ChatGLM、DeepSeek、OpenAI、Claude、Gemini等
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger('AIJian')


class BaseModelAdapter(ABC):
    """模型适配器基类"""
    
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.kwargs = kwargs
        self.logger = logger
    
    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    def analyze_image(self, image_path: str, prompt: str, **kwargs) -> str:
        """分析图像"""
        pass


class TongyiAdapter(BaseModelAdapter):
    """通义千问适配器"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化客户端"""
        try:
            import dashscope
            dashscope.api_key = self.api_key
            self.client = dashscope
            self.logger.info("✅ 通义千问客户端初始化成功")
        except Exception as e:
            self.logger.error(f"❌ 通义千问客户端初始化失败: {e}")
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        if not self.client:
            raise Exception("通义千问客户端未初始化")
        
        try:
            from dashscope import Generation
            
            response = Generation.call(
                model='qwen-max',
                prompt=prompt,
                **kwargs
            )
            
            if response.status_code == 200:
                return response.output.text
            else:
                raise Exception(f"API调用失败: {response.message}")
        
        except Exception as e:
            self.logger.error(f"❌ 通义千问文本生成失败: {e}")
            raise
    
    def analyze_image(self, image_path: str, prompt: str, **kwargs) -> str:
        """分析图像"""
        if not self.client:
            raise Exception("通义千问客户端未初始化")
        
        try:
            from dashscope import MultiModalConversation
            
            # 构造本地文件的 file:// URI。
            # 注意：dashscope SDK 内部会简单地把前缀 "file://" 去掉再按本地路径读取；
            # 在 Windows 上，如果传入 pathlib.as_uri() 得到 "file:///F:/..."，
            # 它去掉前缀后会变成 "/F:/..."，导致找不到文件。
            # 因此这里对 Windows 做专门处理，保证最终传给 SDK 的实际文件路径是 "F:/..."。
            try:
                p = Path(image_path).resolve()
                if os.name == 'nt':
                    # Windows: 生成类似 file://F:/path/to/img.jpg 的形式
                    path_str = p.as_posix()
                    img_uri = f'file://{path_str}'
                else:
                    # POSIX: 直接使用合法的 file:///path 形式
                    img_uri = p.as_uri()
            except Exception:
                # 兜底：保持与旧版本一致的简单拼接（使用原始路径字符串）
                img_uri = f'file://{image_path}'

            messages = [{
                'role': 'user',
                'content': [
                    {'image': img_uri},
                    {'text': prompt}
                ]
            }]
            
            response = MultiModalConversation.call(
                model='qwen-vl-max',
                messages=messages,
                **kwargs
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                raise Exception(f"API调用失败: {response.message}")
        
        except Exception as e:
            self.logger.error(f"❌ 通义千问图像分析失败: {e}")
            raise


class WenxinAdapter(BaseModelAdapter):
    """文心一言适配器"""
    
    def __init__(self, api_key: str, secret_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.secret_key = secret_key
        self.access_token = None
        self._get_access_token()
    
    def _get_access_token(self):
        """获取access token"""
        try:
            import requests
            
            url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.api_key}&client_secret={self.secret_key}"
            response = requests.post(url)
            
            if response.status_code == 200:
                self.access_token = response.json().get('access_token')
                self.logger.info("✅ 文心一言access token获取成功")
            else:
                raise Exception(f"获取access token失败: {response.text}")
        
        except Exception as e:
            self.logger.error(f"❌ 文心一言access token获取失败: {e}")
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        if not self.access_token:
            raise Exception("文心一言access token未获取")
        
        try:
            import requests
            
            url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={self.access_token}"
            
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                **kwargs
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                return response.json().get('result', '')
            else:
                raise Exception(f"API调用失败: {response.text}")
        
        except Exception as e:
            self.logger.error(f"❌ 文心一言文本生成失败: {e}")
            raise
    
    def analyze_image(self, image_path: str, prompt: str, **kwargs) -> str:
        """分析图像"""
        # 文心一言的图像分析功能
        raise NotImplementedError("文心一言图像分析功能待实现")


class ChatGLMAdapter(BaseModelAdapter):
    """ChatGLM适配器"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化客户端"""
        try:
            from zhipuai import ZhipuAI
            self.client = ZhipuAI(api_key=self.api_key)
            self.logger.info("✅ ChatGLM客户端初始化成功")
        except Exception as e:
            self.logger.error(f"❌ ChatGLM客户端初始化失败: {e}")
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        if not self.client:
            raise Exception("ChatGLM客户端未初始化")
        
        try:
            response = self.client.chat.completions.create(
                model="glm-4",
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            self.logger.error(f"❌ ChatGLM文本生成失败: {e}")
            raise
    
    def analyze_image(self, image_path: str, prompt: str, **kwargs) -> str:
        """分析图像"""
        if not self.client:
            raise Exception("ChatGLM客户端未初始化")
        
        try:
            import base64
            
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            response = self.client.chat.completions.create(
                model="glm-4v",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                        {"type": "text", "text": prompt}
                    ]
                }],
                **kwargs
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            self.logger.error(f"❌ ChatGLM图像分析失败: {e}")
            raise


class DeepSeekAdapter(BaseModelAdapter):
    """DeepSeek适配器"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化客户端"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
            self.logger.info("✅ DeepSeek客户端初始化成功")
        except Exception as e:
            self.logger.error(f"❌ DeepSeek客户端初始化失败: {e}")
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        if not self.client:
            raise Exception("DeepSeek客户端未初始化")
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            self.logger.error(f"❌ DeepSeek文本生成失败: {e}")
            raise
    
    def analyze_image(self, image_path: str, prompt: str, **kwargs) -> str:
        """分析图像"""
        raise NotImplementedError("DeepSeek暂不支持图像分析")


class OpenAIAdapter(BaseModelAdapter):
    """OpenAI适配器"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = base_url
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化客户端"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.logger.info("✅ OpenAI客户端初始化成功")
        except Exception as e:
            self.logger.error(f"❌ OpenAI客户端初始化失败: {e}")
    
    def generate_text(self, prompt: str, model: str = "gpt-4", **kwargs) -> str:
        """生成文本"""
        if not self.client:
            raise Exception("OpenAI客户端未初始化")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            self.logger.error(f"❌ OpenAI文本生成失败: {e}")
            raise
    
    def analyze_image(self, image_path: str, prompt: str, model: str = "gpt-4-vision-preview", **kwargs) -> str:
        """分析图像"""
        if not self.client:
            raise Exception("OpenAI客户端未初始化")
        
        try:
            import base64
            
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }],
                **kwargs
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            self.logger.error(f"❌ OpenAI图像分析失败: {e}")
            raise


class ClaudeAdapter(BaseModelAdapter):
    """Claude适配器"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化客户端"""
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.logger.info("✅ Claude客户端初始化成功")
        except Exception as e:
            self.logger.error(f"❌ Claude客户端初始化失败: {e}")
    
    def generate_text(self, prompt: str, model: str = "claude-3-opus-20240229", **kwargs) -> str:
        """生成文本"""
        if not self.client:
            raise Exception("Claude客户端未初始化")
        
        try:
            message = self.client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            
            return message.content[0].text
        
        except Exception as e:
            self.logger.error(f"❌ Claude文本生成失败: {e}")
            raise
    
    def analyze_image(self, image_path: str, prompt: str, model: str = "claude-3-opus-20240229", **kwargs) -> str:
        """分析图像"""
        if not self.client:
            raise Exception("Claude客户端未初始化")
        
        try:
            import base64
            
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            message = self.client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}},
                        {"type": "text", "text": prompt}
                    ]
                }],
                **kwargs
            )
            
            return message.content[0].text
        
        except Exception as e:
            self.logger.error(f"❌ Claude图像分析失败: {e}")
            raise


class GeminiAdapter(BaseModelAdapter):
    """Gemini适配器"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化客户端"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai
            self.logger.info("✅ Gemini客户端初始化成功")
        except Exception as e:
            self.logger.error(f"❌ Gemini客户端初始化失败: {e}")
    
    def generate_text(self, prompt: str, model: str = "gemini-pro", **kwargs) -> str:
        """生成文本"""
        if not self.client:
            raise Exception("Gemini客户端未初始化")
        
        try:
            model_instance = self.client.GenerativeModel(model)
            response = model_instance.generate_content(prompt, **kwargs)
            return response.text
        
        except Exception as e:
            self.logger.error(f"❌ Gemini文本生成失败: {e}")
            raise
    
    def analyze_image(self, image_path: str, prompt: str, model: str = "gemini-pro-vision", **kwargs) -> str:
        """分析图像"""
        if not self.client:
            raise Exception("Gemini客户端未初始化")
        
        try:
            from PIL import Image
            
            img = Image.open(image_path)
            model_instance = self.client.GenerativeModel(model)
            response = model_instance.generate_content([prompt, img], **kwargs)
            return response.text
        
        except Exception as e:
            self.logger.error(f"❌ Gemini图像分析失败: {e}")
            raise


class MultiModelManager:
    """多模型管理器"""
    
    def __init__(self):
        """初始化多模型管理器"""
        self.logger = logger
        self.adapters: Dict[str, BaseModelAdapter] = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        try:
            from backend.config.ai_config import get_config_manager
            self.config_manager = get_config_manager()
            self.logger.info("✅ 多模型管理器配置加载成功")
        except Exception as e:
            self.logger.error(f"❌ 多模型管理器配置加载失败: {e}")
            self.config_manager = None
    
    def get_adapter(self, model_type: str) -> Optional[BaseModelAdapter]:
        """获取模型适配器"""
        if model_type in self.adapters:
            return self.adapters[model_type]
        
        if not self.config_manager:
            return None
        
        try:
            if model_type == 'tongyi':
                api_key = (self.config_manager.llm_config.tongyi_api_key
                           or self.config_manager.llm_config.qwen_api_key)
                if api_key:
                    adapter = TongyiAdapter(api_key)
                    self.adapters[model_type] = adapter
                    return adapter
            
            elif model_type == 'wenxin':
                api_key = (self.config_manager.llm_config.wenxin_api_key
                           or self.config_manager.llm_config.ernie_api_key)
                secret_key = (self.config_manager.llm_config.wenxin_secret_key
                              or self.config_manager.llm_config.ernie_secret_key)
                if api_key and secret_key:
                    adapter = WenxinAdapter(api_key, secret_key)
                    self.adapters[model_type] = adapter
                    return adapter
            
            elif model_type == 'chatglm':
                api_key = self.config_manager.llm_config.chatglm_api_key
                if api_key:
                    adapter = ChatGLMAdapter(api_key)
                    self.adapters[model_type] = adapter
                    return adapter
            
            elif model_type == 'deepseek':
                api_key = self.config_manager.llm_config.deepseek_api_key
                if api_key:
                    adapter = DeepSeekAdapter(api_key)
                    self.adapters[model_type] = adapter
                    return adapter
            
            elif model_type == 'openai':
                api_key = self.config_manager.llm_config.custom_api_key
                base_url = self.config_manager.llm_config.custom_base_url
                if api_key:
                    adapter = OpenAIAdapter(api_key, base_url)
                    self.adapters[model_type] = adapter
                    return adapter
            
            elif model_type == 'claude':
                api_key = (self.config_manager.llm_config.claude_api_key
                           or self.config_manager.llm_config.anthropic_api_key)
                if api_key:
                    adapter = ClaudeAdapter(api_key)
                    self.adapters[model_type] = adapter
                    return adapter
            
            elif model_type == 'gemini':
                api_key = self.config_manager.llm_config.gemini_api_key
                if api_key:
                    adapter = GeminiAdapter(api_key)
                    self.adapters[model_type] = adapter
                    return adapter
        
        except Exception as e:
            self.logger.error(f"❌ 获取{model_type}适配器失败: {e}")
        
        return None
    
    def generate_text(self, prompt: str, model_type: Optional[str] = None, **kwargs) -> str:
        """生成文本"""
        if not model_type and self.config_manager:
            model_type = self.config_manager.llm_config.default_model
        
        adapter = self.get_adapter(model_type)
        if not adapter:
            raise Exception(f"无法获取{model_type}模型适配器")
        
        return adapter.generate_text(prompt, **kwargs)
    
    def analyze_image(self, image_path: str, prompt: str, model_type: Optional[str] = None, **kwargs) -> str:
        """分析图像
        
        优先使用视觉配置中的默认模型，并将视觉模型别名映射到已有适配器类型：
        - qwen_vl/qianwen_vl -> tongyi（通义千问VL）
        - gpt4v/openai        -> openai
        - baidu               -> wenxin
        - gemini/gemini_vision-> gemini
        如果默认视觉模型没有可用适配器，则按通义VL → OpenAI → Claude → Gemini 顺序回退。
        """

        # 1. 若未显式指定 model_type，则从视觉配置中获取默认值
        if not model_type and self.config_manager:
            model_type = getattr(self.config_manager.vision_config, 'default_model', None) or 'qwen_vl'

        # 2. 将视觉模型别名映射到适配器类型
        def _normalize(model: str) -> str:
            m = (model or '').lower()
            if m in ('qwen_vl', 'qianwen_vl', 'tongyi_vl'):
                return 'tongyi'
            if m in ('gpt4v', 'openai_vision', 'openai'):
                return 'openai'
            if m in ('baidu', 'wenxin', 'wenxin_vision'):
                return 'wenxin'
            if m in ('gemini', 'gemini_vision'):
                return 'gemini'
            return m

        normalized = _normalize(model_type) if model_type else None

        # 3. 尝试获取适配器；若失败则按优先级回退
        adapter = self.get_adapter(normalized) if normalized else None

        if not adapter:
            # 按用户常用模型顺序回退（通义VL -> OpenAI -> Claude -> Gemini）
            fallback_order = ['tongyi', 'openai', 'claude', 'gemini']
            for mt in fallback_order:
                adapter = self.get_adapter(mt)
                if adapter:
                    self.logger.info(f"🔁 视觉模型回退到: {mt} (原始: {model_type})")
                    break

        if not adapter:
            raise Exception(f"无法获取{model_type or '视觉'}模型适配器")

        return adapter.analyze_image(image_path, prompt, **kwargs)


# 全局多模型管理器实例
_multi_model_manager = None


def get_multi_model_manager() -> MultiModelManager:
    """获取多模型管理器单例"""
    global _multi_model_manager
    if _multi_model_manager is None:
        _multi_model_manager = MultiModelManager()
    return _multi_model_manager
