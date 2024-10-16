import re

def count_characters(text):
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    english_pattern = re.compile(r'[a-zA-Z]+')
    other_pattern = re.compile(r'[^\u4e00-\u9fffa-zA-Z]+')

    chinese_characters = chinese_pattern.findall(text)
    english_characters = english_pattern.findall(text)
    other_characters = other_pattern.findall(text)

    chinese_count = sum(len(char) for char in chinese_characters)
    english_count = sum(len(char) for char in english_characters)
    other_count = sum(len(char) for char in other_characters)

    return chinese_count, english_count, other_count


model_config = {
    "ERNIE-3.5-8K":{
        "Pricing": (0.0008, 0.002),
        "currency_symbol": '￥',
    },
    "ERNIE-4.0-8K":{
        "Pricing": (0.03, 0.09),
        "currency_symbol": '￥',
    },
    "ERNIE-Novel-8K":{
        "Pricing": (0.04, 0.12),
        "currency_symbol": '￥',
    }
}

class ChatMessages(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.model = kwargs['model'] if 'model' in kwargs else None
        
        assert 'currency_symbol' not in kwargs
    
    def __getitem__(self, index):
        result = super().__getitem__(index)
        if isinstance(index, slice):
            return ChatMessages(result, model=self.model)
        return result
    
    def __add__(self, other):
        if isinstance(other, list):
            return ChatMessages(super().__add__(other), model=self.model)
        return NotImplemented 

    def count_message_tokens(self):
        if self.model in model_config:
            return self.get_estimated_tokens()
        else:
            from tokencost import count_message_tokens  # 和gradio库冲突
            return count_message_tokens(self, self.model)
    
    def copy(self):
        return ChatMessages(self, model=self.model)
    
    def get_estimated_tokens(self):
        num_tokens = 0
        for message in self:
            for key, value in message.items():
                chinese_count, english_count, other_count = count_characters(value)
                num_tokens += chinese_count + english_count // 5 + other_count
        return num_tokens
    
    @property
    def cost(self):
        if len(self) == 0:
            return 0
        
        if self.model in model_config:
            return model_config[self.model]["Pricing"][0] * self[:-1].count_message_tokens() / 1_000 + model_config[self.model]["Pricing"][1] * self[-1:].count_message_tokens() / 1_000
        else:
            from tokencost import calculate_all_costs_and_tokens
            details = calculate_all_costs_and_tokens(self[:-1].get_estimated_tokens(), self[-1:], self.model)
            return details['completion_cost'] + details['prompt_cost']
    
    @property
    def response(self):
        return self[-1]['content']
    
    @property
    def currency_symbol(self):
        if self.model in model_config:
            return model_config[self.model]["currency_symbol"]
        else:
            return '$'
    

