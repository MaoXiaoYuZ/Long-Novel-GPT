import uuid

# 定义了用于Wirter yield的数据类型，同时也是前端展示的“关键点”消息
class KeyPointMsg(dict):
    def __init__(self, title='', subtitle='', prompt_name=''):
        super().__init__()
        if not title and not subtitle and prompt_name:
            pass
        elif title and subtitle and not prompt_name:
            pass
        else:
            raise ValueError('Either title and subtitle or prompt_name must be provided')
        
        self.update({
            'id': str(uuid.uuid4()),
            'title': title,
            'subtitle': subtitle,
            'prompt_name': prompt_name,
            'finished': False
        })

    def set_finished(self):
        assert not self['finished'], 'finished flag is already set'
        self['finished'] = True
        return self # 返回self，方便链式调用

    def is_finished(self):
        return self['finished']
    
    def is_prompt(self):
        return bool(self.prompt_name)
    
    def is_title(self):
        return bool(self.title)
    
    @property
    def id(self):
        return self['id']
    
    @property
    def title(self):
        return self['title']
    
    @property
    def subtitle(self):
        return self['subtitle']
    
    @property
    def prompt_name(self):
        prompt_name = self['prompt_name']
        if len(prompt_name) >= 10:
            return prompt_name[:10] + '...'
        return prompt_name
