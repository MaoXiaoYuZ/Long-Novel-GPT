import re
import json

from layers.writer import Writer

class ChaptersWriter(Writer):
    def __init__(self, output_path, model='gpt-4-1106-preview', sub_model="gpt-3.5-turbo-1106"):
        system_prompt = "我会给你小说的大纲以及某一卷的剧情，需要你创作该卷的分章剧情。你需要遵从我的指令，让我们一起一步步进行章节剧情的创作。首先，我们会创作分章剧情，然后再对每章的剧情进行扩充。同时，对于你创作的剧情，我会要求你反思或根据我给出的意见进行修改。"
        super().__init__(system_prompt, output_path, model, sub_model)
        
        self.chapters = {}

        self.load()
    
    def init_by_outline_writer(self, outline_writer, volume_name):
        context_volume_names = self.get_context_elements_in_list(volume_name, outline_writer.get_volume_names(), context_length=1)
        custom_system_prompt = f"\n\n下面是小说的大纲和卷的剧情：{outline_writer.get_outline_content(context_volume_names)}\n\n非常重要：你要创建的是{volume_name}的分章剧情，其余卷作为上下文参考。"
        self.set_custom_system_prompt(custom_system_prompt)
    
    def get_attrs_needed_to_save(self):
        return [('chapters', 'chapters_content.json'), ('chat_history', 'chapters_chat_history.json')]
    
    def get_chapter_names(self):
        return list(self.chapters.keys())
    
    def get_chapters_content(self, chatper_names=None):
        if chatper_names is None:
            return self.json_dumps(self.chapters)
        else:
            return self.json_dumps({k:v for k, v in self.chapters.items() if k in chatper_names})
    
    def update_chapters(self, chapters):
        self.chapters = chapters

    def init_chapters(self, human_feedback=''):
        if not human_feedback:
            human_feedback = ""
        user_prompt =  "现在开始创作该卷的分章剧情。要注意你创作的是章节剧情梗概，不是正文，不要描述过于细节的东西。\n" + f"意见：{human_feedback}" + '\n' + \
"""你需要以如下JSON格式输出：
{
 "分析": "<结合大纲和意见对分章剧情进行详细的分析>",
 "第1章": {
  "思考": "<结合之前分析对该章剧情进行思考>",
  "剧情": "<这里创作该章剧情>"
 },
 //更多章节，每一章连着前一章
}"""    
        messages = self.get_chat_history(resume=False)
        messages.append({'role':'user', 'content':user_prompt})
        for response_msgs in self.chat(messages, response_json=True):
            yield response_msgs
        response = response_msgs[-1]['content']
        response_json = self.parse_json_block(response_msgs)
        self.chapters = {k:{'剧情': v['剧情']} for k, v in response_json.items() if isinstance(v, dict)}

        context_messages = response_msgs
        if self.get_config('auto_compress_context'):
            context_messages[-2]['content'] = "现在开始创作该卷的分章剧情。要注意你创作的是章节剧情梗概，不是正文，不要描述过于细节的东西。\n" + f"意见：{human_feedback}"
        
        self.update_chat_history(context_messages)

        yield context_messages
    
    def rewrite_chatpers(self, chapter_name=None, human_feedback=None):
        if not human_feedback:
            human_feedback = "请从情节推动不合理，剧情不符合逻辑，条理不清晰等方面进行反思。"

        messages = self.get_chat_history()

        if chapter_name is None:
            input_chapters = self.comment_duplicate_inputs(self.chapters, messages)
            input_chapters = self.json_dumps(input_chapters)
            prompt = f"分章剧情:{input_chapters}\n\n意见：{human_feedback}\n\n你需要先根据意见对分章剧情进行反思，再给出新的剧情。遵照下面的JSON输出格式。" + \
"""{
 "反思": "<根据意见对分章剧情进行反思>",
 "第X章": {
  "思考": "<思考如何修正>",
  "剧情": "<这里重新输出剧情>"
 },
 //更多章节，和输入章节一一对应
}"""  
            prompt = prompt.replace('第X章', self.get_chapter_names()[0])
        else:
            context_chapter_names = self.get_context_elements_in_list(chapter_name, self.get_chapter_names(), context_length=1)
            input_chapters = self.comment_duplicate_inputs({k:v for k,v in self.chapters.items() if k in context_chapter_names}, messages)
            input_chapters = self.json_dumps(input_chapters)
            prompt = f"分章剧情:{input_chapters}\n\n意见：{human_feedback}\n\n你需要先根据意见对第X章剧情进行反思，然后重写第X章剧情。遵照下面的JSON输出格式。" + \
"""{
 "反思": "<根据意见对第X章剧情进行反思>",
 "第X章": {
  "思考": "<思考如何重写>",
  "剧情": "<这里重新输出剧情>"
 }
}"""    
            prompt = prompt.replace('第X章', chapter_name)

        messages.append({'role':'user',  'content': prompt})
            
        response_msgs = yield from self.chat(messages, response_json=True)
        response = response_msgs[-1]['content']

        response_json = self.parse_json_block(response_msgs)
        for title, detail in response_json.items():
            if title in self.chapters:
                self.chapters[title].update({'剧情': detail['剧情']})
                del detail['剧情']
        
        context_messages = response_msgs
        if self.get_config('auto_compress_context'):
            context_prompt = f"意见：{human_feedback}\n\n你需要先根据意见对分章剧情进行反思，再给出新的剧情。"
            if chapter_name is not None:
                context_prompt = context_prompt.replace('分章剧情', chapter_name + "剧情")
            context_messages[len(messages)-1]['content'] = context_prompt
            context_messages[len(messages)]['content'] = self.json_dumps(response_json)

        if self.count_messages_length(context_messages[1:-2]) > self.get_config('chat_context_limit'):
            context_messages = yield from self.summary_messages(context_messages, [1, len(context_messages)-2])

        self.update_chat_history(context_messages)

        yield context_messages
    
    def polish_chatpers(self, chapter_name=None, human_feedback=None):
        if not human_feedback:
            human_feedback = "请从情节推动不合理，剧情不符合逻辑，条理不清晰等方面进行反思。"

        messages = self.get_chat_history()

        context_chapter_names = self.get_context_elements_in_list(chapter_name, self.get_chapter_names(), context_length=1)
        input_chapters = self.comment_duplicate_inputs({k:v for k,v in self.chapters.items() if k in context_chapter_names}, messages)
        input_chapters = self.json_dumps(input_chapters)
        prompt = f"分章剧情:{input_chapters}\n\n意见：{human_feedback}\n\n你需要先根据意见对{chapter_name}剧情进行反思，再对{chapter_name}剧情进行改进。"
        
        messages.append({'role':'user',  'content': prompt})
        chapter_text = self.chapters[chapter_name]['剧情']
        response_msgs,  new_chpater_text = yield from self.prompt_polish(messages, chapter_text)

        self.chapters[chapter_name]['剧情'] = new_chpater_text
        
        context_messages = response_msgs
        if self.get_config('auto_compress_context'):
            context_messages[len(messages)-1]['content'] = f"意见：{human_feedback}\n\n你需要先根据意见对{chapter_name}剧情进行反思，再对{chapter_name}剧情进行改进。"

        if self.count_messages_length(context_messages[1:-2]) > self.get_config('chat_context_limit'):
            context_messages = yield from self.summary_messages(context_messages, [1, len(context_messages)-2])

        self.update_chat_history(context_messages)

        yield context_messages