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
class PayloadType(Enum):
    CALL = "call"
    INTERNAL_CALL = "internal_call"
    OBJECT = "object"      # e.g. knowledge assets (NDN data)
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"

class CallAction(Enum):
    WAIT = "wait"
    START_PROCESSING = "start_processing"
    START_CALLING = "start_calling"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    # Add other actions as needed

# Metadata section

@dataclass
class Metadata:
    msg_id: str = field(default_factory=lambda: "msg#" + uuid.uuid4().hex)
    msg_hash_id: Optional[str] = None  # NDN id
    ts: float = field(default_factory=time.time)
    last_changed_ts: float = field(default_factory=time.time)
    sender: Optional[Dict[SenderType, str]] = field(default_factory=dict)
    receivers: Optional[Dict[ReceiverType, str]] = field(default_factory=dict)
    mention: Optional[str] = None
    session_id: Optional[str] = None

# Content payload section

@dataclass
class Payload:
    type: PayloadType = None
    # For CALL type payloads: 
    action: Optional[CallAction] = None
    # For REQUEST/RESPONSE/BROADCAST types:
    content: Optional[Any] = None
    expect_response_interval: Optional[float] = None  # only for REQUEST
    response_interval: Optional[float] = None           # only for RESPONSE

# Context and reference sections

@dataclass
class Context:
    topic: Optional[str] = None          # session topic
    thread_topic: Optional[str] = None   # message thread topic

@dataclass
class Reference:
    ndn_list: Optional[List[str]] = field(default_factory=list)  # list of referenced NDN objects

# Log section for reasoning trace and function chain

@dataclass
class LogInfo:
    reasoning_trace: Optional[str] = None
    function_call_chain: Optional[List[str]] = field(default_factory=list)

# Control section for status

@dataclass
class Control:
    status: Optional[str] = None

# Root message class combining all sections

@dataclass
class AgentMsg:
    metadata: Metadata = field(default_factory=Metadata)
    content: Payload = field(default_factory=Payload)
    context: Context = field(default_factory=Context)
    reference: Reference = field(default_factory=Reference)
    log: LogInfo = field(default_factory=LogInfo)
    control: Control = field(default_factory=Control)
