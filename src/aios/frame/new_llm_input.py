import json
import copy
import logging
from typing import List, Dict
from .ndn import NDNItem, NDNDataBase


logger = logging.getLogger(__name__)

class LLMPrompt:
    def __init__(self,prompt_str = None) -> None:
        self.messages : List[Dict] = []
        if prompt_str:
            self.messages.append({"role":"user","content":prompt_str})
        self.system_message : Dict = None
        self.inner_functions : List[Dict] = []

    def append_system_message(self,content:str):
        if content is None:
            return

        if self.system_message is None:
            self.system_message = {"role":"system","content":content}
        else:
            self.system_message["content"] += content

    def append_user_message(self,content:str):
        if content is None:
            return

        self.messages.append({"role":"user","content":content})

    def as_str(self)->str:
        result_str = ""
        if self.system_message:
            result_str = json.dumps(self.system_message,ensure_ascii=False)
        if self.messages:
            result_str += json.dumps(self.messages,ensure_ascii=False)
        if self.inner_functions:
            result_str += json.dumps(self.inner_functions,ensure_ascii=False)

        return result_str

    def to_message_list(self):
        result = []
        if self.system_message:
            result.append(self.system_message)
        result.extend(self.messages)
        return result



    def append(self,prompt:'LLMPrompt'):
        if prompt is None:
            return

        if prompt.inner_functions:
            if self.inner_functions is None:
                self.inner_functions = copy.deepcopy(prompt.inner_functions)
            else:
                self.inner_functions.extend(prompt.inner_functions)

        if prompt.system_message is not None:
            if self.system_message is None:
                self.system_message = copy.deepcopy(prompt.system_message)
            else:
                self.system_message["content"] += prompt.system_message.get("content")

        self.messages.extend(prompt.messages)

    def load_from_config(self,config:List[Dict]) -> bool:
        if isinstance(config,list) is not True:
            logger.error("prompt is not list!")
            return False
        self.messages : List[Dict] = []
        for msg in config:
            if msg.get("content"):
                if msg.get("role") == "system":
                    self.system_message = msg
                else:
                    self.messages.append(msg)
            else:
                logger.error("prompt message has no content!")
        return True

class LLMInput:
    def __init__(self, prompt: LLMPrompt = None, NDN_ids: Dict[str, str] = None) -> None:
        self.prompt: LLMPrompt = prompt if prompt else LLMPrompt()
        self.NDN_ids: Dict[str, str] = NDN_ids if NDN_ids else {}
        self.NDN_items: Dict[str, NDNItem] = self._get_items(self.NDN_ids)  # key is the reference, value is NDNItem

    def _get_items(NDN_ids: Dict[str, str]) -> Dict[str, NDNItem]:
        items: Dict[str, NDNItem] = {}
        database = NDNDataBase.get_instance()
        if NDN_ids is None:
            return items

        for ref, name in NDN_ids.items():
            item = database.get_item(name)
            items[ref] = item

        return items
