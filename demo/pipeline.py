import re
import os

from layers.outline_writer import OutlineWriter
from layers.chapters_writer import ChaptersWriter
from layers.novel_writer import NovelWriter

class Long_Novel_GPT_DEMO:
    def __init__(self, output_path, model="gpt-3.5-turbo-1106") -> None:
        self.output_path = output_path
        self.model = model

        self.layers = {}
    
    def get_layer(self, volume_name=None, chapter_name=None):
        key = 'writer'
        if volume_name is None and chapter_name is None:
            layer = self.layers
            if key in layer:
                return layer
            else:
                layer[key] = self.get_outline_writer()
                return layer
            
        elif volume_name is not None and chapter_name is None:
            if volume_name not in self.layers:
                self.layers[volume_name] = layer = {}
            else:
                layer = self.layers[volume_name]

            if key in layer:
                return layer
            else:
                layer[key] = self.get_chapters_writer(self.layers[key], volume_name)
                return layer
        else:
            assert volume_name in self.layers, f"ERROR: 未找到分卷名称：{volume_name}"
            if chapter_name not in self.layers[volume_name]:
                self.layers[volume_name][chapter_name] = layer  = {}
            else:
                layer = self.layers[volume_name][chapter_name]

            if key in layer:
                return layer
            else:
                layer[key] = self.get_novel_writer(self.layers[key], volume_name, self.layers[volume_name][key], chapter_name)
                return layer
    
    def get_writer(self, volume_name=None, chapter_name=None):
        return self.get_layer(volume_name, chapter_name)['writer']
    
    def get_outline_writer(self):
        outline_writer = OutlineWriter(
            output_path=self.output_path,
            model=self.model
        )
        return outline_writer
    
    def get_chapters_writer(self, outline, volume_name):
        assert volume_name in outline.get_volume_names(), f"ERROR: 未找到分卷名称：{volume_name}"
        chapters_writer = ChaptersWriter(
            output_path=os.path.join(self.output_path, volume_name),
            model=self.model
        )
        chapters_writer.init_by_outline_writer(outline, volume_name)
        return chapters_writer

    
    def get_novel_writer(self, outline, volume_name, chapters, chapter_name):
        assert volume_name in outline.get_volume_names(), f"ERROR: 未找到分卷名称：{volume_name}"
        assert chapter_name in chapters.get_chapter_names(), f"ERROR: 未找到章节名称：{chapter_name}"
        novel_writer = NovelWriter(
            output_path=os.path.join(self.output_path, volume_name, chapter_name),
            model=self.model,
        )
        novel_writer.init_by_outline_and_chapters_writer(outline, volume_name, chapters, chapter_name)
        return novel_writer
