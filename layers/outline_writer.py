import re
import json

from layers.writer import Writer

class OutlineWriter(Writer):
    def __init__(self, output_path, model='gpt-4-1106-preview', sub_model="gpt-3.5-turbo-1106"):
        system_prompt = \
"""现在你是一个小说家，正在和我一起合作来创作小说大纲。
小说大纲包括小说设定和分卷剧情。
接下来让我们一步一步来，你需要遵照我的指令逐步完成整个大纲的创作，期间我还可能让你根据我的意见进行修改。
对话的内容如果过长，我会让你进行总结并省略部分对话内容。""" 
        super().__init__(system_prompt, output_path, model, sub_model)

        self.outline = {}

        self.load()

        self.set_config(init_outline_setting = '现在需要你对小说设定进行创作。')
        self.set_config(init_outline_volumes = '现在需要你对分卷剧情进行创作。')
        self.set_config(refine_outline_setting = "之前输出的设定中还有很多可以改进的地方，请进行反思。")
        self.set_config(refine_outline_volumes = "之前输出的分卷剧情还有很多可以改进的地方，请进行反思。")
    
    def get_attrs_needed_to_save(self):
        return [('outline', 'outline_content.json'), ('chat_history', 'outline_chat_history.json')]
    
    def get_volume_names(self):
        return list(self.outline['分卷剧情'].keys()) if '分卷剧情' in self.outline else []
    
    def get_outline_content(self, volume_names=None):
        if volume_names is None:
            volume_names = self.get_volume_names()
        data = {k:v for k, v in self.outline.items() if k != '分卷剧情'}
        if volume_names:
            data['分卷剧情'] = {k:v for k, v in self.outline['分卷剧情'].items() if k in volume_names}
        return self.json_dumps(data)
    
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

        for response_msgs in self.instruction_outline(instruction):
            yield response_msgs
        response = response_msgs[-1]['content']
        response_json = json.loads(response)

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
                pass

    def init_outline_volumes(self, human_feedback=None):
        instruction = \
"""
如果之前已有分卷剧情，那就只输出需要更改的部分JSON。
你需要按照下面JSON格式输出：
{
"分卷剧情":{
"分析": "<这里进行分析/反思>",
"第1卷": {
"分析": "<这里进行分析/反思>", 
"剧情": "<这里创作该卷的剧情>"
},
//更多卷
}
}"""  
        if human_feedback:
            instruction = f"{human_feedback}" + '\n\n' + instruction
        else:
            if "分卷剧情" in self.outline and self.outline['分卷剧情']:
                human_feedback = self.get_config('refine_outline_volumes')
            else:
                human_feedback = self.get_config('init_outline_volumes')
            instruction = instruction

        for response_msgs in self.instruction_outline(instruction):
            yield response_msgs
        response = response_msgs[-1]['content']
        response_json = json.loads(response)

        if '分卷剧情' not in self.outline:
            self.outline['分卷剧情'] = {}

        self.outline['分卷剧情'].update({k:{"剧情": v['剧情']} for k, v in response_json['分卷剧情'].items() if isinstance(v, dict)})

    def instruction_outline(self, human_feedback=None):
        chat_id = 'instruction_outline'
        messages = self.get_chat_history(chat_id)

        if self.outline:
            inputs = self.comment_duplicate_inputs(self.outline, messages)
            inputs = f"输入：{self.json_dumps(inputs)}\n\n"
        else:
            inputs = ""

        user_prompt = inputs + f"指示：{human_feedback}"    
        messages.append({'role':'user', 'content': user_prompt})    
        
        for response_msgs in self.chat(messages, response_json=True):
            yield response_msgs
        
        context_messages = response_msgs
        context_messages[-2]['content'] = f"指示：{human_feedback}"
        if self.count_messages_length(context_messages[1:-2]) > self.get_config('chat_context_limit'):
            for context_messages in self.summary_messages(context_messages, [1, len(context_messages)-2]):
                yield context_messages
        self.chat_history[chat_id] = context_messages

        yield context_messages
    