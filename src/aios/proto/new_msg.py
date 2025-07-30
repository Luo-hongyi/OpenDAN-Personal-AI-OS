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
    MACHINE = "Machine"  # For machine-generated messages

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
    def __init__(self, msg_type: MessageType = MessageType.DEFAULT) -> None:
        # metadata
        self.msg_id: str = "msg#" + uuid.uuid4().hex
        self.ts: float = time.time()

        # routing information
        self.sender: Dict[str, SenderType] = {} # the direct sender of msg
        self.source: Dict[str, SenderType] = {} # the source of msg, different from sender when the msg is forwarded by sender
        self.receivers: Dict[str, SenderType] = {}

        self.metadata: Dict[str, Any] = None
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
        self.msg_type: MessageType = msg_type # different message types have different types of content
        self.content_type: str = ContentType.TEXT
        self.body: Any = None  # Can be any type of content, e.g. text, object, etc. the conten

        # External context
        self.session_topic: str = None  # Topic for session management
        self.thread_topic: str = None  # Topic for thread management
        self.context_objects: Dict[ContextType, Dict[Any, ContentType]] = None # Context objects related to the message, e.g. attachments, mentions, etc.

        # Internal log
        self.function_call_chain: List[str] = None
        self.reasoning_chain: List[str] = None

    def create_agent_request(self, body: Any, content_type: ContentType, metadata: Optional[Dict[str, Any]] = None) -> 'AgentMsg':
        """
         The body  of the agent request message is natural language, which can be processed by an agent.
        """
        agent_request_msg = AgentMsg(msg_type=MessageType.AGENTREQUEST)
        agent_request_msg.body = body
        agent_request_msg.content_type = content_type.value
        if metadata:
            # Add metadata to the agent request message
            agent_request_msg.metadata = metadata
        return agent_request_msg
    
    def create_machine_call(self, body: Any, metadata: Optional[Dict[str, Any]] = None) -> 'AgentMsg':
        """
         The body  of the machine call message is a JSON packed function call, which can be processed by a service or another machine.
        """
        machine_call_msg = AgentMsg(msg_type=MessageType.MACHINECALL)

        # check if body is a valid function call, require function id and parameters
        if not isinstance(body, dict) or 'function_id' not in body or 'parameters' not in body:
            raise ValueError("Body must be a valid function call with 'function_id' and 'parameters' keys.")
        
        machine_call_msg.body = body
        machine_call_msg.content_type = "formated_text"  # Assuming the body is a formatted text for machine calls
        if metadata:
            # Add metadata to the machine call message
            machine_call_msg.metadata = metadata
        return machine_call_msg
    
    def create_notification(self, body: Any, content_type: ContentType, metadata: Optional[Dict[str, Any]] = None) -> 'AgentMsg':
        notification_msg = AgentMsg(msg_type=MessageType.NOTIFICATION)
        notification_msg.body = body
        notification_msg.content_type = content_type.value
        if metadata:
            # Add metadata to the notification message
            notification_msg.metadata = metadata
        return notification_msg
    
    def create_response(self, body: Any, content_type: ContentType, metadata: Optional[Dict[str, Any]] = None) -> 'AgentMsg':
        response_msg = AgentMsg(msg_type=MessageType.RESPONSE)
        content_type = content_type.value
        response_msg.body = body
        if metadata:
            # Add metadata to the response message
            response_msg.metadata = metadata
        return response_msg
    
    def set_routing_info(self, sender: Dict[str, SenderType], 
                         source: Dict[str, SenderType], 
                         receivers: Dict[str, ReceiverType]) -> None:
        """
        Set the routing information for the message.
        """
        self.sender = sender
        self.source = source
        self.receivers = receivers

    def set_context_info(self, session_topic: str = None, thread_topic: str = None) -> None:
        """
        Set the context information for the message.
        """
        self.session_topic = session_topic
        self.thread_topic = thread_topic
        

    def add_context_object(self, context_type: ContextType, content_type: ContentType, context_object: Any) -> None:
        """
        Add a context object to the message.
        """
        if self.context_objects is None:
            self.context_objects = {}
        if context_type not in self.context_objects:
            self.context_objects[context_type] = {}

        self.context_objects[context_type][context_object] = content_type

    def set_log(self, function_call_chain: List[str] = None, reasoning_chain: List[str] = None) -> None:
        """
        Set the internal log for the message.
        """
        if function_call_chain is not None:
            self.function_call_chain = function_call_chain
        if reasoning_chain is not None:
            self.reasoning_chain = reasoning_chain
    