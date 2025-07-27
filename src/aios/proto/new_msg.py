from dataclasses import dataclass, field
from enum import Enum
import uuid
import time
from typing import Dict, List, Any, Optional

# Enums for standardized types

class SenderType(Enum):
    USER = "User"
    SYSTEM = "System"
    AGENT = "Agent"
    ENV = "Env"

class ReceiverType(Enum):
    USER = "User"
    SYSTEM = "System"
    AGENT = "Agent"
    MACHINE = "Machine"
    GROUP = "Group"  # For group messages
    ALL = "All"      # For broadcast messages
class MessageType(Enum):
    # message type describe the intent of the message, payload of the message varies by type
    DEFAULT = "default"
    AGENTREQUEST = "agent_request" # request to a node that can read natural language, content is natural language
    MACHINECALL = "machine_call" # call a node that can not read natural language, content is a json packed function call
    NOTIFICATION = "notification" # dose not require response
    RESPONSE = "response" # response to a call
class AgentAction(Enum): # workflow control
    # actions that can be performed by the agent
    WAIT = "wait" # ask the agent to wait for more messages to come before processing
    START = "start" # ask the agent to start processing the message
    ACTIVATE = "activate" # ask the agent to activate itself
    DEACTIVATE = "deactivate" # ask the agent to deactivate itself
    UPDATE = "update" # ask the agent to update itself

class ContentType(Enum):
    TEXT = "text"  # plain text content
    FORMATEDTEXT = "formated_text" # 
    BASE64 = "base64"  # base64 encoded content
    URL = "url"  # URL to external content
    NDN_NAME = "ndn_name"  # NDN name for content

class ContextType(Enum):
    # context type describe the relationship between the message and the context
    ATTACHMENT = "attachment" 
    MENTION = "mention" # mention a user or agent in the message
    QUOTE = "quote" # quote a message
    REPLY = "reply" # reply to a message
    EXAMPLE = "example" # for few-shot prompting
    FORMAT = "format" # format the message in a specific way

class AgentMsgStatus(Enum):
    RESPONSED = 0
    INIT = 1
    SENDING = 2
    PROCESSING = 3
    ERROR = 4
    RECVED = 5
    EXECUTED = 6

class AgentMsg:
    # metadata
    msg_id: str = "msg#" + uuid.uuid4().hex
    ts: float = time.time()

    # routing information
    sender: Dict[SenderType, str] = {} # the direct sender of msg
    source: Dict[SenderType, str] = {} # the source of msg, different from sender when the msg is forwarded by sender
    receivers: Dict[ReceiverType, str] = {}

    metadata: Dict[str, Any] = None
    """
    the metadata include optional fields that can be used to store additional information about the message
    metadata:
    {
        # extra routing info
        "mention": List[str],  # list of user/agent names mentioned in the message
        "topic_id": str,  # topic id for the message
        "thread_id": str,  # thread id for the message
        "session_id": str,  # session id for the message
        "msg_content_id": str,  # content id for the message
        "prev_msg_id": str, # id of the last message
        "last_modified": double,  # last modified timestamp
        "last_modifier": str, # id of the node that modify the msg
        "is_from_packed_msg": bool # Whether the message is from a larger msg pack, 图文混编时分多条消息一起发送时使用
        "pack_id": str # the pack id 
        "in_pack_id": str # the position of the message in pack, "1, 2, 3... EOP(end of pack)"
        
        # extra payload info
        "agent_action": AgentAction # common simple action provided by Agent, for agent request
        "introduction": str # the introduction of return data asset, for response
        "report": str # report message when calling service, for reponse

        # extra status info
        "status": AgentMsgStatus,  # status of the message
        "is_NDN_data": bool,  # Whether the message is stored as NDN data
        "response_msg_ids": list[str], # response to a specific msg
        "expect_response_interval": float,  # expected response interval for the message
        "response_interval": float,  # response interval for the message
    }
    """

    # payload
    msg_type: MessageType = MessageType.DEFAULT # different message types have different types of content
    content_type: str = ContentType.TEXT
    content: Any = None  # Can be any type of content, e.g. text, object, etc. the conten

    # External context
    session_topic: str = None  # Topic for session management
    thread_topic: str = None  # Topic for thread management
    context_objects: Dict[ContextType,Any] = None

    # Internal log
    function_call_chain: List[str] = None
    reasoning_chain: List[str] = None