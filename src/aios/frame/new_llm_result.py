import json
import shlex
from enum import Enum
from typing import List
from ..proto.ai_function import ActionNode
from ..proto.new_agent_msg import AgentMsg


class LLMResultStates(Enum):
    IGNORE = "ignore"
    OK = "ok" # process done
    ERROR = "error"

class LLMResult:
    def __init__(self) -> None:
        self.state : str = LLMResultStates.IGNORE
        self.compute_error_str = None
        self.resp : str = "" # llm say:
        self.raw_result = None # raw result from compute kernel
        self.action_list : List[ActionNode] = [] # op_list is a optimize design for saving token


    @classmethod
    def from_error_str(self,error_str:str) -> 'LLMResult':
        r = LLMResult()
        r.state = LLMResultStates.ERROR
        r.error_str = error_str
        return r

    @classmethod
    def from_json_str(self,llm_json_str:str) -> 'LLMResult':
        r = LLMResult()
        if llm_json_str is None:
            r.state = LLMResultStates.IGNORE
            return r
        if llm_json_str == "**IGNORE**":
            r.state = LLMResultStates.IGNORE
            return r

        r.state = LLMResultStates.OK

        llm_json = json.loads(llm_json_str)
        r.resp = llm_json.get("resp")
        r.raw_result = llm_json
        action_list = llm_json.get("actions")
        if action_list:
            for action in action_list:
                action_item = ActionNode.from_json(action)
                if action_item:
                    r.action_list.append(action_item)

        return r

    @classmethod
    def parse_action(cls,func_string:str):
        str_list = shlex.split(func_string)
        func_name = str_list[0]
        params = str_list[1:]
        return func_name, params

    @classmethod
    def from_str(self,llm_result_str:str,valid_func:List[str]=None) -> 'LLMResult':
        r = LLMResult()

        if llm_result_str is None:
            r.state = LLMResultStates.IGNORE
            return r
        if llm_result_str == "**IGNORE**":
            r.state = LLMResultStates.IGNORE
            return r

        try:
            if llm_result_str[0] == "{":
                return LLMResult.from_json_str(llm_result_str)

            if llm_result_str.lstrip().rstrip().startswith("```json"):
                return LLMResult.from_json_str(llm_result_str[7:-3])
        except:
            pass

        lines = llm_result_str.splitlines()
        is_need_wait = False

        def check_args(action_item:ActionNode):
            match action_item.name:
                case "post_msg":# /post_msg $target_id
                    if len(action_item.args) != 1:
                        return False

                    new_msg = AgentMsg()
                    target_id = action_item.args[0]
                    msg_content = action_item.body
                    new_msg.set("",target_id,msg_content)

                    return True


            return False


        current_action : ActionNode = None
        for line in lines:
            if line.startswith("##/"):
                if current_action:
                    if check_args(current_action) is False:
                        r.resp += current_action.dumps()
                    else:
                        r.action_list.append(current_action)

                action_name,action_args = LLMResult.parse_action(line[3:])
                current_action = ActionNode(action_name,action_args)
            else:
                if current_action:
                    current_action.append_body(line + "\n")
                else:
                    r.resp +=  s + "\n"

        if current_action:
            if check_args(current_action) is False:
                r.resp += current_action.dumps()
            else:
                r.action_list.append(current_action)

        r.state = LLMResultStates.OK
        return r