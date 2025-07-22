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
    GROUP = "Group"  # For group messages
    ALL = "All"      # For broadcast messages
class MessageType(Enum):
    # message type describe the intent of the message, payload of the message varies by type
    DEFAULT = "default"
    CALL = "call" # ask the agent to perform some action
    INTERNAL_CALL = "internal_call" # the agent self calls some function
    OBJECT = "object" # any object, e.g. file, image, NDN name, etc.
    REQUEST = "request" # request for some response
    RESPONSE = "response" # response to a request
    BROADCAST = "broadcast" # broadcast message to all agents
    READ = "read" # the agent read a NDN data

class CallAction(Enum):
    # actions that can be performed by the agent
    DEFAULT = "default"
    WAIT = "wait" # ask the agent to wait for more messages to come before processing
    START = "start" # ask the agent to start processing the message
    ACTIVATE = "activate" # ask the agent to activate itself
    DEACTIVATE = "deactivate" # ask the agent to deactivate itself
    UPDATE = "update" # ask the agent to update itself
    FORWARD = "forward" # ask the agent to forward the message to another agent

class ContextType(Enum):
    # context type describe the relationship between the message and the context
    ATTACHMENT = "attachment" # 
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
    msg_NDN_id: str = None  # NDN id
    ts: float = time.time()
    last_changed_ts: float = time.time()
    sender: Dict[SenderType, str] = {}
    receivers: Dict[ReceiverType, str] = {}
    mention: List[str] = None
    session_id: str = None
    thread_id: str = None  # For message threads

    # payload
    msg_type: MessageType = MessageType.DEFAULT
    action: CallAction = None
    content: Any = None  # Can be any type of content, e.g. text, object, etc.
    expect_response_interval: float = None
    response_interval: float = None

    # External context
    session_topic: str = None  # Topic for session management
    thread_topic: str = None  # Topic for thread management
    context_objects: Dict[ContextType,Any] = None

    # Internal log
    function_call_chain: List[str] = None
    reasoning_chain: List[str] = None

    # status of the message
    status: AgentMsgStatus = AgentMsgStatus.INIT
    is_NDN_data: bool = False  # Whether the message is NDN data