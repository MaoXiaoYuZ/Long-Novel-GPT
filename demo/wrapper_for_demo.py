import os
import json

from demo.pipeline import Long_Novel_GPT_DEMO

class Long_Novel_GPT_Wrapper(Long_Novel_GPT_DEMO):
    def __init__(self, output_path, model="gpt-3.5-turbo-1106") -> None:
        super().__init__(output_path, model)

        self.total_api_cost = 0
        self.writer_config = {}

        self.layers = {
            'outline': {'curr_checkpoint_i': -1},
            'chapters': {'curr_checkpoint_i': -1},
            'novel': {'curr_checkpoint_i': -1},
        }

    def init(self):
        for layer_name in self.layers.keys():
            self.save(layer_name)
        self.save_checkpoints()
    
    def get_layer(self, layer_name=None):
        layer = self.layers[layer_name]
        return layer
    
    def set_writer_config(self, config):
        self.writer_config = config
    
    def get_writer(self, layer_name):
        writer = super().get_writer(layer_name)
        if 'chat_context_limit' in self.writer_config:
            writer.set_config(chat_context_limit=self.writer_config['chat_context_limit'])
        if 'auto_compress_context' in self.writer_config:
            writer.set_config(auto_compress_context=self.writer_config['auto_compress_context'])
        return writer
        
    def save_checkpoints(self):
        filename = os.path.join(self.output_path, "app.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.layers, f, ensure_ascii=False, indent=4)
    
    def load_checkpoints(self):
        filename = os.path.join(self.output_path, "app.json")
        with open(filename, 'r', encoding='utf-8') as f:
            self.layers = json.load(f)
        
        for layer_name, layer in self.layers.items():
            writer = self.get_writer(layer_name)
            writer.load(os.path.join(writer.output_path, ".checkpoints", f"checkpoint_{layer['curr_checkpoint_i']}"))

    def get_cur_checkpoint_i(self, layer_name):
        layer = self.get_layer(layer_name)
        return layer['curr_checkpoint_i']
    
    def save(self, layer_name):
        layer, writer = self.get_layer(layer_name), self.get_writer(layer_name)
        cur_checkpoint_i = layer['curr_checkpoint_i'] + 1
        checkpoint_path = os.path.join(writer.output_path, ".checkpoints", f"checkpoint_{cur_checkpoint_i}")
        os.makedirs(checkpoint_path, exist_ok=True)
        writer.save(checkpoint_path)
        layer['curr_checkpoint_i'] = cur_checkpoint_i
        self.save_checkpoints()
    
    def rollback(self, i, layer_name):
        layer, writer = self.get_layer(layer_name), self.get_writer(layer_name)

        cur_checkpoint_i = layer['curr_checkpoint_i'] - i
        if cur_checkpoint_i < 0:
            return False
        else:
            checkpoint_path = os.path.join(writer.output_path, ".checkpoints", f"checkpoint_{cur_checkpoint_i}")
            writer.load(checkpoint_path)
            layer['curr_checkpoint_i'] = cur_checkpoint_i
            self.save_checkpoints()
            return True
    