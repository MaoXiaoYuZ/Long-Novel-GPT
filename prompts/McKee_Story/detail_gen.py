import os
import sys
from jinja2 import Environment, FileSystemLoader
from typing import List
from pydantic import BaseModel
from openai import OpenAI
import json


project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)
from prompts.McKee_Story.start import StoryGenerator, append_to_extracted_info, save_json
from prompts.McKee_Story.data_schma import CharacterModel, ChapterModel, CharacterRelationshipMap, RelationshipModel




class detail_story_generator(StoryGenerator):
    def __init__(self):
        super().__init__()

    def generate_story_chapters(self,variables):
        rendered = self.load_template('5.戏剧八要素章节生成.jinja2',variables)
        
        extracted_chapters = """
        请仔细分析故事中的每一章节内容，提取以下信息:

        1. 章节编号
        2. 章节标题
        3. 章节内容概要

        要求:
        - 每个章节需要包含完整的故事情节和情感发展
        - 保持章节之间的连贯性和故事发展的合理性
        - 突出每个章节的主要冲突和转折点
        - 注意人物性格的一致性和成长变化
        - 确保每个章节都推动整体故事的发展

        输出格式:
        {
                    "chapter1_title": "章节标题",
                    "chapter1_content": "章节内容概要"

                ..........
                提取出现的每一章节
        }

        请确保提取的内容完整， 每一章节都要有标题和内容，准确,并保持故事的连贯性，没有的章节留空，不要提取不存在的章节。
        """

        chapters = self.generate_story(rendered, 
                                   system_prompt="你是小说章节生成器，输出需要符合给定格式的章节内容。")
        
        result = self.extract_important_information(chapters, extracted_chapters, ChapterModel)
        
        if result:
            append_to_extracted_info({"chapters":chapters}, 'json_data/extracted_info_生活的转折点.json')
            save_json(result, 'json_data/chapters_《生活的转折点》.json')
            print("章节生成成功")
            return result
        else:
            print("章节生成失败")
            return None


    def gen_story_character(self,variables):
        rendered = self.load_template('6.重要角色生成.jinja2',
                                      variables)
        characters = self.generate_story(rendered, 
                            system_prompt="你是小说角色生成器，输出需要符合给定格式的角色内容，要符合故事逻辑，以及主角的外部矛盾。",    
                            model='gpt-4o-mini-2024-07-18'
                            )
        

        extracted_characters = """
        请仔细分析故事中的每一章节内容，提取以下信息:

        1. 角色名称
        2. 角色性格
        3. 角色外貌
        4. 角色关系
        5. 角色内部外部冲突
        """
        result = self.extract_important_information(characters, extracted_characters, CharacterModel)

        if result:
            append_to_extracted_info({"characters":characters}, 'json_data/chapters_《生活的转折点》.json')
            save_json(result, 'json_data/characters_《生活的转折点》.json')
            print("角色生成成功")
            return result
        else:
            print("角色生成失败")
            return None

    def gen_character_relationship_map(self,variables, variables_2=None ):
        if variables_2:
            variables["story_outline"] = variables_2["story_outline"]
        print("#######################&&角色图生成&&#############################")
        print("")
        关系图生成 = self.load_template('8.关系图生成.jinja2',
                                      variables)
        
        
        print("#######################&&关系图生成&&#############################")
        print("")
        
        角色图生成 = self.load_template('7.角色图生成.jinja2',
                                      variables)




        characters_map = self.generate_story(角色图生成, 
                            system_prompt="你是小说角色地图，根据故事大纲的角色逻辑，输出需要符合给定格式的角色地图，要符合故事逻辑，以及角色的外部矛盾。",    
                            model='gpt-4o-mini-2024-07-18'
                            )
        

        relationship_map = self.generate_story(关系图生成, 
                    system_prompt="你是小说角色关系地图，根据故事大纲的角色逻辑，输出需要符合给定格式的角色与角色的关系地图，要符合大纲故事逻辑，要根据角色关系推断角色之间的关系(配角到配角)。",    
                    model='gpt-4o-mini-2024-07-18'
                    )

        
        
        
        extracted_characters_map = """
        请仔细分析故事中的每一章节内容，提取以下信息:

        1. name: 角色名称
        2. gender: 性别
        3. importance: 重要性(1-5)
        4. alignment: 立场(good/neutral/evil)
        5. role_type: 角色类型(protagonist/supporting/antagonist)
        6. inner_outer_conflict: 内外矛盾
        7. personality: 性格特征

        如果角色关系中没有出现，则留空
        """


        extracted_relationship_map = """
        请仔细分析故事中的每一章节内容，提取以下信息:

        1. source: 关系起点角色
        2. target: 关系终点角色
        3. closeness: 亲密度(0-1)
        4. relationship_type: 关系类型(mentor/friend/colleague/antagonist等)
        5. explanation: 关系说明

        如果角色关系中没有出现，则留空
        """

        print("#######################角色网#############################")
        character_relationship_map = self.extract_important_information(characters_map, extracted_characters_map, CharacterRelationshipMap)
        print("")
        print(character_relationship_map)
        print("")

        relationship_map = self.extract_important_information(relationship_map, extracted_relationship_map, RelationshipModel)
        print("#######################关系网#############################")
        print("")
        print(relationship_map)
        print("")




        save_json(relationship_map, 'json_data/relationship_map_《生活的转折点》.json')
        save_json(character_relationship_map, 'json_data/character_relationship_map_《生活的转折点》.json')

if __name__ == '__main__':
    detail_story_generator = detail_story_generator()

    json_file = 'json_data/extracted_info_生活的转折点.json'
    character_json_file = 'json_data/characters_《生活的转折点》.json'


    with open(character_json_file, 'r', encoding='utf-8') as file:
        ss = json.load(file)

    with open(json_file, 'r', encoding='utf-8') as file:
        ss_2 = json.load(file)

        # detail_story_generator.generate_story_chapters(ss)
        detail_story_generator.gen_character_relationship_map(ss, ss_2)




