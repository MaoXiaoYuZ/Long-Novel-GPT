import re
import json

# import sys, os
# sys.path.append(os.path.abspath(os.path.join(__file__, '../..')))   

from layers.writer import ChatMessages, Writer

class NovelWriter(Writer):
    def __init__(self, output_path, model='gpt-4-1106-preview', sub_model="gpt-3.5-turbo-1106"):
        system_prompt = f'现在你是一个小说家，你需要根据大纲和章节剧情对某一章的正文进行创作。'
        super().__init__(system_prompt, output_path, model, sub_model)
        
        self.text = ''

        self.load()
    
    def init_by_outline_and_chapters_writer(self, outline_writer, volume_name, chapters_writer, chapter_name):
        context_chapter_names = self.get_context_elements_in_list(chapter_name, chapters_writer.get_chapter_names())
        chapters_context = chapters_writer.get_chapters_content(context_chapter_names)
        custom_system_prompt = f"\n\n下面是小说的大纲和分卷剧情:\n{outline_writer.get_outline_content(volume_names=[volume_name, ])}\n\n下面是小说中{volume_name}的分章剧情:\n{chapters_context}\n\n非常重要：你要创建的是{volume_name}的{chapter_name}的正文，其余卷或章作为上下文参考。"
        self.set_custom_system_prompt(custom_system_prompt)
    
    def get_attrs_needed_to_save(self):
        return [('text', 'novel_text.json'), ('chat_history', 'novel_chat_history.json')]

    def init_text(self, human_feedback=None):
        user_prompt = human_feedback + '\n\n' + \
"""接下来开始对该章的正文进行创作。你需要直接输出正文，不掺杂任何其他内容。
"""
        chat_id = 'init_text'
        
        messages = self.get_chat_history(chat_id, resume=False)

        messages.append({'role':'user', 'content': user_prompt})

        for response_msgs in self.chat(messages, response_format=None):
            yield response_msgs
        response = response_msgs[-1]['content']
        
        self.text = response
        
        context_messsages = response_msgs
        context_messsages[-1]['content'] = "(已省略)"
        self.chat_history[chat_id] = context_messsages
    
    def refine_text(self, human_feedback=None):
        if not human_feedback:
            human_feedback = "请从不符合逻辑，不符合人设，不符合大纲等方面进行反思。"

        chat_id = 'refine_text'
        messages = self.get_chat_history(chat_id, inherit='init_text')

        input_text = '已省略，见上文。' if self.string_in_messages(self.text, messages) else self.text
        messages.append({
            'role':'user', 
            'content': f"正文：{input_text}\n\n意见：{human_feedback}\n\n" + \
"""请根据意见对正文进行反思, 再改进。
请严格按照下面JSON格式输出：
{
 "反思": "<根据意见进行反思>",
 "修正一": {
  "问题分析": "<分析正文中存在的问题>",
  "参考文本": "<这里给出参考剧情中的句子或片段>",
  "改进方案": "<这里分析要如何改进>",
  "修正文本": "<这里输出改进后的文本>"
 },
 //列出更多修正，修正二，修正三，等
}
"""
        })

        for response_msgs in self.chat(messages, response_format={"type": "json_object"}):
            yield response_msgs
        response = response_msgs[-1]['content']
        response_json = json.loads(response)

        for response_revise_msgs in self.replace_text_by_review(self.text, response_json):
            yield response_revise_msgs

        corrected_chapter_detail = response_revise_msgs[-1]['content']

        self.text = corrected_chapter_detail

        context_messages = response_msgs[:-2]
        context_messages.append({'role':'user', 'content': f"意见：{human_feedback}\n\n请根据意见对正文进行反思。"})
        for v in response_json.values():
            if isinstance(v, dict):
                if '修正文本' in v and '参考文本' in v:
                    del v['修正文本']
                    del v['参考文本']
        context_messages.append({'role':'assistant', 'content': self.json_dumps(response_json)})
        context_messages.append({'role':'user', 'content': "很好，请根据反思内容，重新输出正文。"})
        context_messages.append({'role':'assistant', 'content': f"修改后的正文:\n(已省略)"})
        if self.count_messages_length(context_messages[1:-4]) > self.get_config('chat_context_limit'):
            for context_messages in self.summary_messages(context_messages, [1, len(context_messages)-4]):
                yield context_messages

        self.chat_history[chat_id] = context_messages

        yield context_messages
    
    def replace_text_by_review(self, text, review):
        context_messages = [
            {
                'role':'user', 
                'content': self.json_dumps({'输入文本': text}) + '\n\n' + f"意见：{review}"
            }]
        
        cost = 0
        for k, v in review.items():
            if isinstance(v, dict) and '修正文本' in v and '参考文本' in v:
                ref_text, replace_text = v['参考文本'], v['修正文本']
                if ref_text in text:
                    text = text.replace(ref_text, replace_text)
                else:
                    prompt = f"请问上述意见中：“{ref_text}”在原文中的对应句是什么，请以如下JSON格式回复。" + '{"对应句":"..."}'        
                    for i in range(3):
                        messages = context_messages + [{'role':'user', 'content': prompt}, ]
                        for response_msgs in self.chat(messages, model=self.get_sub_model(), response_format={"type": "json_object"}):
                            yield response_msgs
                        cost += response_msgs.cost
                        ref_text = json.loads(response_msgs[-1]['content'])['对应句']
                        if ref_text in text:
                            text = text.replace(ref_text, replace_text)
                            break
                    else:
                        print(f"ERROR:无法找到{ref_text}在原文中的对应句！")
        
        yield ChatMessages(context_messages + [{'role':'assistant', 'content': text}], model=self.get_sub_model(), cost=cost)


text =  "韩轩站在长满野草的图书馆废墟前，地面的裂缝中攀爬着顽强的植物，而昔日的文明只剩下这些由砖与石堆砌成的断壁残垣。深知徒劳与重复的日子中，这片默默承载着时光的庙堂，成了他唯一心灵的港湾。\n\n他推开腐朽的门扉，阵阵尘土伴随着诉说无言故事的气息扑面而来。书架依然矗立着，或许它们已不再记得被顾客翻阅的温度。韩轩的目光却更多地停留在书架上书本的排列方式和地面尘埃的厚度上。每一个细节都成了他的线索，每一个不一致都指引着一个可能的出口。\n\n他深吸一口气，心中默念着循环前一天的记忆，确信自己并未疯狂。然后，他开始了熟悉的例行公事——检查每一行书架，记录每本书的位置，每次来访都要认真地比对着昨日的笔记。今天，他注意到了《历史述要》较着上个周期移动了几分之几厘米，而且有几页似乎翻过了，折角的痕迹分外新鲜。\n\n他知道这些细微的变化不可能是无意之举，肯定藏着某种由未知力量制造的模式。韩轩盯着那本书，它仿佛代表了一个巨大的迷宫的入口，而他，是即将踏入其中的探险者。\n\n于是，韩轩开始了他的记录工作，从那些被世界遗忘的书页中搜寻解密时间的钥匙。他的笔尖在笔记上飞舞，记录着每一天发现的每一个小差异。他的目光变得坚定，眼中映着重获自由的渴望。\n\n尽管知道外面的世界仍然在无止境、无变化地重复着，韩轩的心却不再感到困顿。他确信，这些小小的破绽终将指引他找到破解虚纪元枷锁的办法。他坚信，历史的尘埃之下藏有逃离重复宿命的秘密。透过每一页翻动的声响，他听到了时间中断的平行乐章在远处低低回响。"
review = {'反思': '现有的正文可能不能充分地体现主人公韩轩在混乱世界中追寻线索的焦虑和矛盾感。情节的推动过于直接，没有充分展开描述他内心的挣扎和反常现象背后的潜在规律。应加强故事的逻辑性，使韩轩的发现和行动更加合理，同时对他的心理变化进行更深入的剖析。', '修正一': {'问题分析': '描述韩轩在图书馆中注意到书的变化有些唐突，未能表现出循环的微妙变异是如何逐步引起他注意的。', '参考文本': '他推开腐朽的门扉，阵阵尘土伴随着诉说无言故事的气息扑面而来...', '改进方案': '可以更细致地讲述韩轩如何观察循环中的细节，并在多次重复后逐渐意识到规律。', '修正文本': '韩轩每天走进图书馆，总是先洒下一点水，看着它们渗透进历史的尘埃中。他开始关注门旁阵阵扑出的尘土，每次的厚度，每次落在封面上的位置似乎都略有不同。'}, '修正二': {'问题分析': '在描述《历史述要》书本的位置和折角变化时，未解释这些变化是怎样触动韩轩心中一连串的疑问和行动。', '参考文本': '今天，他注意到了《历史述要》较着上个周期移动了几分之几厘米，而且有几页似乎翻过了...', '改进方案': '描写时应该更详细地体现韩轩是如何把这些不一致性关联起来，并由此引起他深入探究的决心。', '修正文本': '发现《历史述要》位置的微小移动后，韩轩凝视着新出现的折角，思绪翻飞。他回忆每一次的访问，那些一丝不苟的记录蓦然串联起令人不安的规律。他意识到，不一致或许是突破循环的钥匙，他必须深入挖掘每一次变化背后的真相。'}, '修正三': {'问题分析': '描述韩轩变得坚定和心中映着重获自由的渴望可能太突兀，缺少内心冲突和情绪变化的渲染。', '参考文本': '尽管知道外面的世界仍然在无止境、无变化地重复着，韩轩的心却不再感到困顿...', '改进方案': '应融入韩轩内心的波动，并描述他是如何逐渐由疑惑到坚定的过程。', '修正文本': '每一天的重复，韩轩的内心都像沙漠中的流沙一般无助而又茫然。然而，在这一刻，当他再次见证了昨日与今日之间那若隐若现的差异时，深藏的不甘和渴望像潮水般涌动。他承认了自己对自由的极致渴慕，而这渴望在理智的指引下渐渐凝聚成坚定的信念。'}}


if __name__ == '__main__':
    writer = NovelWriter('output/test')
    for msgs in writer.replace_text_by_review(text, review):
        pass
    print(msgs)