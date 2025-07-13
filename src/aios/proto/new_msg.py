from abc import ABC
import uuid
import time
import json
from enum import Enum
from typing import Tuple, List, Dict, Any

class AgentMsgType(Enum):
    TYPE_INSTRUCTION = 0
    TYPE_RESPONSE = 1

class AgentMsgStatus(Enum):
    RESPONSED = 0
    INIT = 1
    SENDING = 2
    PROCESSING = 3
    ERROR = 4
    RECVED = 5
    EXECUTED = 6

class InstructionType(Enum):
    TEXT = 0
    ACTION = 1
    EVENT = 2

class AttachmentType(Enum):
    TEXT = 0
    NDN = 1
    MSG = 2
    FUNCTION = 3

class ProductType(Enum):
    KNOWLEDGE = 0

class AgentMsg(ABC):
    def __init__(self):
        self.msg_id = "msg#" + uuid.uuid4().hex
        self.source:str = None
        self.targets:List[str] = None
        self.session_id:str = None

        self.create_time = 0
        self.done_time = 0

        self.status:AgentMsgStatus = AgentMsgStatus.INIT


class InstructionMsg(AgentMsg):
    def __init__(self, instructions:List[Dict[InstructionType, Any]], attachments:List[Dict[AttachmentType, Any]] = None):
        super().__init__()
        self.type = AgentMsgType.TYPE_INSTRUCTION
        self.instructions = instructions
        self.attachments = attachments

class ResponseMsg(AgentMsg):
    def __init__(self, response:str, products:List[Dict[str, Any]] = None):
        super().__init__()
        self.type = AgentMsgType.TYPE_RESPONSE
        self.response = response
        self.products = products


