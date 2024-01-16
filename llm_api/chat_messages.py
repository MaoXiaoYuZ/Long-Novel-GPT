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

class ChatMessages(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = kwargs['model'] if 'model' in kwargs else None
        self.cost = kwargs['cost'] if 'cost' in kwargs else None
        self.currency_symbol = kwargs['currency_symbol'] if 'currency_symbol' in kwargs else None
    
    def __getitem__(self, index):
        result = super().__getitem__(index)
        if isinstance(index, slice):
            return ChatMessages(result, model=self.model, cost=self.cost, currency_symbol=self.currency_symbol)
        return result
    
    def __add__(self, other):
        if isinstance(other, list):
            return ChatMessages(super().__add__(other), model=self.model, cost=self.cost, currency_symbol=self.currency_symbol)
        return NotImplemented 
    
    def get_estimated_tokens(self):
        num_tokens = 0
        for message in self:
            for key, value in message.items():
                chinese_count, english_count, other_count = count_characters(value)
                num_tokens += chinese_count + english_count // 5 + other_count
        return num_tokens
