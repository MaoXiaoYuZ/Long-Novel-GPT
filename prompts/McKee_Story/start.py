import os
import sys
from jinja2 import Environment, FileSystemLoader
from typing import List
from pydantic import BaseModel
from openai import OpenAI
import json

# 获取项目根目录的绝对路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# 现在可以导入 config 了
from config import API_SETTINGS
from llm_api.openai_api import stream_chat_with_gpt

# 设置模板目录
template_dir = os.path.dirname(os.path.abspath(__file__))
print("模板目录:", template_dir)

# 列出目录中的所有文件
print("目录中的文件:")
for file in os.listdir(template_dir):
    print(f"- {file}")

# 检查文件是否存在
template_path = os.path.join(template_dir, "1.初始变量.jinja2")

print(f"模板文件路径: {template_path}")
print(f"文件是否存在: {os.path.exists(template_path)}")

# 使用 UTF-8 编码设置
env = Environment(
    loader=FileSystemLoader(template_dir, encoding='utf-8')
)



class ExtractionModel(BaseModel):
    incentive_event: List[str]
    character_name: List[str]
    character_age: List[int]
    character_job: List[str]
    character_inner_confilt: List[str]
    character_outer_confilt: List[str]
    world_setting: List[str]
    history_background: List[str]
    social_structure: List[str]


def save_json(data, filename):
    """
    将数据保存为JSON格式文件
    
    Args:
        data: 要保存的数据
        filename: 保存的文件名
    """
    # 如果不是字典类型,尝试转换为字典
    if not isinstance(data, dict):
        try:
            if isinstance(data, str):
                data = json.loads(data)
            else:
                data = dict(data)
        except Exception as e:
            print(f"无法将数据转换为JSON格式: {str(e)}")
            return False
            
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"数据已成功保存到 {filename}")
        return True
    except Exception as e:
        print(f"保存JSON文件时出错: {str(e)}")
        return False


def append_to_extracted_info(new_data, filename):
    try:
        if not isinstance(new_data, dict):
            new_data = dict(new_data)   
        # 读取现有的JSON文件
        with open(filename, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        
        # 确保现有数据是字典
        if not isinstance(existing_data, dict):
            print("现有数据不是字典格式，无法追加新数据。")
            return False
        
        # 将新数据追加到现有数据中
        existing_data.update(new_data)
        
        # 保存更新后的数据
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)
        
        print(f"新数据已成功追加到 {filename}")
        return True
    except json.JSONDecodeError as e:
        print(f"JSON 解码错误: {str(e)}")
        return False
    except Exception as e:
        print(f"处理文件时出错: {str(e)}")
        return False



class StoryGenerator:
    def __init__(self, model='gpt-4o-mini', 
                 api_key=API_SETTINGS['gpt']['api_key'], 
                 base_url=API_SETTINGS['gpt']['base_url'], 
                 proxies=API_SETTINGS['gpt']['proxies']):
        """
        初始化StoryGenerator类
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.proxies = proxies
        self.json_file = None
    def generate_story(self, prompt, system_prompt="你是小说生成器，输出需要符合给定格式的内容。", model=None):
        if model is None:
            model = self.model
        # 跟踪上一次的响应长度
        last_response_length = 0
        
        # 存储完整的响应内容
        full_response = ""
        
        for response in stream_chat_with_gpt(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            model=model,
            api_key=self.api_key,
            base_url=self.base_url,
            proxies=self.proxies,
        ):
            # 只打印新增的内容
            current_content = response[-1]['content']
            new_content = current_content[last_response_length:]
            print(new_content, end='', flush=True)
            last_response_length = len(current_content)
            full_response = current_content

        return full_response






    def load_template(self,template_name,variables=None):
        if variables is None:
            variables = {}
        # 加载模板  
        template = env.get_template(template_name)

        # 渲染变量模板
        rendered = template.render(**variables)
        print("####################################################")
        print("")
        print(rendered)
        print("")
        print("####################################################")

        return rendered


    def generate_story_character_detail(self,variables):
        """
        使用模板生成故事内容
        
        Args:
            variables (dict): 包含故事变量的字典,用于填充模板
            
        Returns:
            str: 生成的故事内容
            
        流程:
        1. 使用load_template加载并渲染角色润色模板
        2. 将渲染后的内容传给generate_story生成最终故事
        """
        rendered = self.load_template('2.角色润色promt.jinja2',variables)
        return self.generate_story(rendered,
                                   system_prompt="你是故事生成器，你生成的故事需要符合三幕式结构，并且需要符合现实给出的格式。")



    def extract_important_information(self, result, extract_prompt, format_class):
        """
        提取重要信息
        """
        client = OpenAI(
            api_key=API_SETTINGS['gpt']['api_key'],
            base_url=API_SETTINGS['gpt']['base_url']
        )

        print("####################################################")
        print("Result before extraction:", result)
        print("---------------------------------------------------")
        print("")
        print("Extract prompt:", extract_prompt)
        print("")
        print("####################################################")

        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "system", "content": extract_prompt},
                {
                    "role": "user", 
                    "content": result,
                },
            ],
            response_format=format_class,
        )

        extracted_info = completion.choices[0].message

        # If the model refuses to respond, you will get a refusal message
        if (extracted_info.refusal):
            result = json.dumps(extracted_info.refusal, indent=2, ensure_ascii=False)
            print(result)
        else:
            result = json.dumps(extracted_info.parsed.dict(), indent=2, ensure_ascii=False)
            print(result)


        return result


    def generate_story_three_act_structure(self,variables):
        """
        使用模板生成三幕式结构大纲
        
        Args:
            variables (dict): 包含故事变量的字典,用于填充模板
            
        Returns:
            str: 生成的三幕式结构大纲
        """


        # 使用模板生成三幕式结构大纲
        rendered = self.load_template('4.三幕式结构大纲生成.jinja2',variables)
        return self.generate_story(rendered)




    def generate_story_outline(self, variables):
        """
        生成故事大纲
        """
        self.json_file = f'json_data/extracted_info_{variables["title"]}.json'
        # 第一步: 生成故事大纲
        rendered = self.load_template('2.角色润色promt.jinja2', variables)
        result = self.generate_story(rendered)
        print("####################################################")
        if result is None or result == "":
            print("生成故事大纲失败")
            return None
        
        # 第二步: 提取重要信息
        extract_prompt = self.load_template('3.提取激励事件等变量.jinja2', {'result': result})
        result = self.extract_important_information(result, extract_prompt, ExtractionModel)
        
        # 将提取的信息保存为JSON文件
        if save_json(result, f'json_data/extracted_info_{variables["title"]}.json'):
            print(f"提取的信息已保存到 json_data/extracted_info_{variables['title']}.json")
        else:
            print(f"提取的信息保存失败")
        
        
        # 将故事大纲追加到提取的信息中
        story_info = {
            "story_title": variables["title"],
            "story_genre": variables["genre"],
            "story_style": variables["style"],
            "story_length": variables["story_length"],
            "story_character_appearance": variables["character_appearance"],
        }
        append_to_extracted_info(story_info, self.json_file)

        # 第三步: 生成三幕式结构大纲
        result_dict = json.loads(result)
        generated_story = self.generate_story_three_act_structure(result_dict)
        
        print("####################################################")
        print(type(generated_story))
        print(generated_story)
        print("####################################################")
        # 检查 generated_story 是否为空或无效
        if not generated_story:
            print("生成的故事为空或无效")
            return None
        
        try:
            # 尝试解析 JSON
            story_outline = json.loads(generated_story)
            # 将故事大纲追加到提取的信息中
            if append_to_extracted_info({'story_outline': story_outline}, self.json_file):
                print("故事大纲已成功追加到提取的信息中")
            else:
                print("追加故事大纲失败")
        except json.JSONDecodeError as e:
            print(f"JSON 解码错误: {str(e)}")
            # 如果解析失败，直接使用原始文本
            if append_to_extracted_info({'story_outline': generated_story}, self.json_file):
                print("故事大纲已成功追加到提取的信息中") 
            else:
                print("追加故事大纲失败")
        
        return generated_story




if __name__ == '__main__':
    # 生成故事大纲的变量，保证大纲的精调
    variables = {
        'style': '现实主义',
        'genre': '短篇小说', 
        'title': '《生活的转折点》',
        'name_character': '李明',
        'age_character': '35',
        'job_character': '中学教师',
        'inner_confilt_character': '希望在平凡的生活中寻找改变和突破',
        'inner_confilt_character': '对现状的不满与改变的犹豫之间的矛盾',
        'outer_confilt_character': '工作压力与家庭责任的冲突',
        'world_setting': '现代都市生活',
        'supporting_character_name': '王芳',
        'supporting_character_age': '32',
        'supporting_character_occupation': '银行职员',
        'character_relationship': '夫妻关系,互相理解但存在沟通障碍',
        'story_length': '8000字',
        'character_appearance': '中等身材,戴眼镜的中年男性,略显疲惫但眼神坚定'
    }


    story_generator = StoryGenerator(model='gpt-4o-mini-2024-07-18')

    story_generator.generate_story_outline(variables)


    # extract_prompt = story_generator.load_template('3.提取激励事件等变量.jinja2')
    # result = story_generator.extract_important_information(test, extract_prompt)
    # print("####################################################")
    # print("")
    # print(result)
    # print("")
    # print("####################################################")
    # generate_story_with_template('1.初始变量.jinja2',variables)