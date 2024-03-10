import os

from layers.outline_writer import OutlineWriter
from layers.chapters_writer import ChaptersWriter
from layers.novel_writer import NovelWriter

class Long_Novel_GPT_DEMO:
    def __init__(self, output_path, model="gpt-3.5-turbo-1106") -> None:
        self.output_path = output_path
        self.model = model

        self.init_layers()

    def init_layers(self):
        self.outline_writer = self.get_outline_writer()
        self.chapters_writer = self.get_chapters_writer(self.outline_writer)
        self.novel_writer = self.get_novel_writer(self.outline_writer, self.chapters_writer)

    def get_writer(self, layer_name):
        return eval(f"self.{layer_name}_writer")
    
    def get_outline_writer(self):
        outline_writer = OutlineWriter(
            output_path=os.path.join(self.output_path, 'outline_writer'),
            model=self.model
        )
        return outline_writer
    
    def get_chapters_writer(self, outline):
        chapters_writer = ChaptersWriter(
            output_path=os.path.join(self.output_path, 'chapters_writer'),
            model=self.model
        )
        chapters_writer.init_by_outline_writer(outline)
        return chapters_writer

    
    def get_novel_writer(self, outline, chapters):
        novel_writer = NovelWriter(
            output_path=os.path.join(self.output_path, 'novel_writer'),
            model=self.model,
        )
        novel_writer.init_by_outline_and_chapters_writer(outline, chapters)
        return novel_writer
