from typing import Dict, Any, Optional, Generator
from .baidu_api import stream_chat_with_wenxin, wenxin_model_config
from .chat_messages import ChatMessages

class ModelConfig(dict):
    def __init__(self, model: str, **options):
        super().__init__(**options)
        self['model'] = model
        self.validate()

    def validate(self):
        if self['model'] in wenxin_model_config:
            for key in ['ak', 'sk']:
                if key not in self:
                    raise ValueError(f"Missing required key: {key}")
        else:
            raise ValueError(f"Unsupported model: {self['model']}")


    def get_api_keys(self) -> Dict[str, str]:
        return {k: v for k, v in self.items() if k not in ['model']}

def stream_chat(model_config: ModelConfig, messages: list) -> Generator:
    if isinstance(model_config, dict):
        model_config = ModelConfig(**model_config)
    
    model_config.validate()
    
    result = yield from stream_chat_with_wenxin(
        messages,
        model=model_config['model'],
        ak=model_config['ak'],
        sk=model_config['sk'],
    )

    return result

# 导出必要的函数和配置
__all__ = ['ChatMessages', 'stream_chat', 'wenxin_model_config', 'ModelConfig']
