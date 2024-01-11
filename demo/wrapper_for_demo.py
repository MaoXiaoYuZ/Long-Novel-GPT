import os
import json

from demo.pipeline import Long_Novel_GPT_DEMO

class Long_Novel_GPT_Wrapper(Long_Novel_GPT_DEMO):
    def __init__(self, output_path, model="gpt-3.5-turbo-1106") -> None:
        super().__init__(output_path, model)

        self.total_api_cost = 0
        self.writer_config = {}
    
    def get_layer(self, volume_name=None, chapter_name=None):
        layer = super().get_layer(volume_name, chapter_name)
        if 'curr_checkpoint_i' not in layer:
            layer['curr_checkpoint_i'] = -1
        return layer
    
    def set_writer_config(self, config):
        self.writer_config = config
    
    def get_writer(self, volume_name=None, chapter_name=None):
        writer = super().get_writer(volume_name, chapter_name)
        if 'chat_context_limit' in self.writer_config:
            writer.set_config(chat_context_limit=self.writer_config['chat_context_limit'])
        return writer
        
    def save_checkpoints(self):
        def deep_copy(obj):
            return {k:deep_copy(v) if isinstance(v, dict) else v for k, v in obj.items() if k != 'writer'}

        filename = os.path.join(self.output_path, "app.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(deep_copy(self.layers), f, ensure_ascii=False, indent=4)
    
    def load_checkpoints(self):
        self.layers = {}
        filename = os.path.join(self.output_path, "app.json")
        with open(filename, 'r', encoding='utf-8') as f:
            checkpoints = json.load(f)
        if 'curr_checkpoint_i' in checkpoints:
            layer = self.get_layer()
            layer['curr_checkpoint_i'] = checkpoints['curr_checkpoint_i']

            layer['writer'].load(os.path.join(layer['writer'].output_path, ".checkpoints", f"checkpoint_{layer['curr_checkpoint_i']}"))
        
        for volume_name, v in checkpoints.items():
            if not isinstance(v, dict):
                continue
            layer = self.get_layer(volume_name)
            layer['curr_checkpoint_i'] = v['curr_checkpoint_i']
            layer['writer'].load(os.path.join(layer['writer'].output_path, ".checkpoints", f"checkpoint_{layer['curr_checkpoint_i']}"))

            for chapter_name, v2 in v.items():
                if not isinstance(v2, dict):
                    continue
                layer = self.get_layer(volume_name, chapter_name)
                layer['curr_checkpoint_i'] = v2['curr_checkpoint_i']
                layer['writer'].load(os.path.join(layer['writer'].output_path, ".checkpoints", f"checkpoint_{layer['curr_checkpoint_i']}"))

    def save(self, volume_name=None, chapter_name=None):
        layer = self.get_layer(volume_name, chapter_name)
        writer, cur_checkpoint_i = layer['writer'], layer['curr_checkpoint_i'] + 1
        checkpoint_path = os.path.join(writer.output_path, ".checkpoints", f"checkpoint_{cur_checkpoint_i}")
        os.makedirs(checkpoint_path, exist_ok=True)
        writer.save(checkpoint_path)
        layer['curr_checkpoint_i'] = cur_checkpoint_i
        self.save_checkpoints()
    
    def rollback(self, i, volume_name=None, chapter_name=None):
        layer = self.get_layer(volume_name, chapter_name)
        writer = layer['writer']

        cur_checkpoint_i = layer['curr_checkpoint_i'] - i
        if cur_checkpoint_i == -1:
            layer.clear()
            layer['curr_checkpoint_i'] = -1
            self.save_checkpoints()
            return True
        elif cur_checkpoint_i < -1:
            return False
        else:
            checkpoint_path = os.path.join(writer.output_path, ".checkpoints", f"checkpoint_{cur_checkpoint_i}")
            writer.load(checkpoint_path)
            layer['curr_checkpoint_i'] = cur_checkpoint_i
            self.save_checkpoints()
            return True
    