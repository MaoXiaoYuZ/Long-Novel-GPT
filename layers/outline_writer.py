import re
import json

from layers.writer import Writer

class OutlineWriter(Writer):
    def __init__(self, output_path, model='gpt-4-1106-preview', sub_model="gpt-3.5-turbo-1106"):
        system_prompt = \
"""现在你是一个小说家，正在和我一起合作来创作小说大纲。
接下来让我们一步一步来，你需要遵照我的指令逐步完成整个大纲的创作，期间我还可能让你根据我的意见进行修改。
对话的内容如果过长，我会让你进行总结并省略部分对话内容。""" 
        super().__init__(system_prompt, output_path, model, sub_model)

        self.outline = {}

        self.idea = ''

        self.load()

        self.set_config(init_outline_setting = '现在需要你对小说设定进行创作。')
        self.set_config(refine_outline_setting = "之前输出的设定中还有很多可以改进的地方，请进行反思。")
    
    def init_by_idea(self, idea):
        self.idea = idea
    
    def get_input_context(self):
        return self.idea
    
    def get_output(self):
        return self.json_dumps(self.outline)
    
    def set_output(self, outline):
        if isinstance(outline, str):
            outline = self.json_load(outline)
        assert isinstance(outline, dict), 'set_output:The type of outline must be dict!'
        self.outline = outline
    
    def get_attrs_needed_to_save(self):
        return [('outline', 'outline_content.json'), ('chat_history', 'outline_chat_history.json'), ('idea', 'idea.json')]

    def get_outline_content(self):
        data = {k:v for k, v in self.outline.items()}
        return self.json_dumps(data) if data else ''
    
    def update_outline(self, outline):
        self.outline = outline
    
    def init_outline_setting(self, human_feedback=None):
        instruction = \
"""
你需要以JSON格式输出新的小说大纲。
输出格式：
{
"分析": "<这里进行分析/反思>", // 这个键必须存在，用于分析/反思
"<设定名>": { // 设定名可以是：人名，物体名，功法名，地点名，某个概念的名称等等。
"操作": "<填 新增/修改>",
"分析": "<这里进行分析/反思>",
"描述": "<在该字符串中创作该设定的具体内容>"  // 描述必须是一个字符串，不能为字典或列表
},
"<设定名>": {
"操作": "<填 保留/删除>"  // 保留或删除设定不需要填写分析和描述
},
// 更多设定，除了新增设定名，其余和输入中设定名一一对应
}"""  
        if human_feedback:
            instruction = f"{human_feedback}" + '\n\n' + instruction
        else:
            if self.outline:
                human_feedback = self.get_config('refine_outline_setting')
            else:
                human_feedback = self.get_config('init_outline_setting')
            instruction = instruction

        if 'chatgpt' in self.get_model() and self.get_chat_history()[0]['role'] == 'system':
            instruction = self.get_chat_history()[0]['content'] + '\n\n' + instruction

        response_msgs = yield from self.instruction_outline(instruction)
        response = response_msgs[-1]['content']
        response_json = self.parse_json_block(response_msgs)

        for setting_name, setting_content in response_json.items():
            if setting_name == "分析":
                continue
            if setting_content['操作'] == '新增':
                self.outline[setting_name] = setting_content['描述']
            elif setting_content['操作'] == '修改':
                self.outline[setting_name] = setting_content['描述']
            elif setting_content['操作'] == '删除':
                if setting_name in self.outline:
                    del self.outline[setting_name]
            elif setting_content['操作'] == '保留':
                if '描述' in setting_content:
                    self.outline[setting_name] = setting_content['描述']

    def instruction_outline(self, human_feedback=None):
        messages = self.get_chat_history()

        if self.outline:
            inputs = self.comment_duplicate_inputs(self.outline, messages)
            inputs = f"输入：{self.json_dumps(inputs)}\n\n"
        else:
            inputs = ""

        user_prompt = inputs + f"指示：{human_feedback}"    
        messages.append({'role':'user', 'content': user_prompt})    
        
        response_msgs = yield from self.chat(messages, response_json=True)

        context_messages = response_msgs
        if self.get_config('auto_compress_context'):
            context_messages[-2]['content'] = f"指示：{human_feedback}"
        
        if self.count_messages_length(context_messages[1:-2]) > self.get_config('chat_context_limit'):
            context_messages = yield from self.summary_messages(context_messages, [1, len(context_messages)-2])
        self.update_chat_history(context_messages)

        return context_messages
    