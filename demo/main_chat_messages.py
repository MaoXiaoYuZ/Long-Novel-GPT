import time
import json
import os

from llm_api.chat_messages import ChatMessages
from concurrent.futures import ThreadPoolExecutor

main_chat_messages_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main_chat_messages.json")

def update_main_chat_messages(msgs:ChatMessages):
    with open(main_chat_messages_path, "w", encoding='utf-8') as file:
        kwargs = {k:getattr(msgs, k) for k in ['cost', 'model', 'currency_symbol']}
        msgs = msgs[:-1] + [{**msgs[-1], 'kwargs':kwargs}, ]
        json.dump(msgs, file, ensure_ascii=False)

update_main_chat_messages(ChatMessages([{}]))

def yield_join(fn, /, *args, **kwargs):
    with ThreadPoolExecutor() as executor:
        future = executor.submit(fn, *args, **kwargs)

        last_modified_time = os.path.getmtime(main_chat_messages_path)
        while True:
            time.sleep(0.02)
            try:
                current_modified_time = os.path.getmtime(main_chat_messages_path)

                if current_modified_time > last_modified_time:
                    last_modified_time = current_modified_time
                    with open(main_chat_messages_path, "r", encoding='utf-8') as file:
                        try:
                            msgs = json.loads(file.read())
                            kwargs = msgs[-1].pop('kwargs')
                            msgs = ChatMessages(msgs, **kwargs)
                        except json.JSONDecodeError:
                            pass
                        else:
                            yield msgs
            except FileNotFoundError:
                pass

            if future.done():
                return future.result()        
        
        
        

    
    
