### 1. Agent的交互对象
1. 用户
2. 环境
3. Agent

用户：
1. ~~接受用户指令~~接受用户的消息：（指令+附件）
2. 接受用户审查
3. 提供结果反馈

环境：
1. 请求知识
2. 执行行动
3. 记录知识

Agent：
1. 发送指令（树状，有上下级之分）
2. 协商问题（群组，没有上下级之分）

用户与Agent的聊天行为如何解释？
当用户与Agent聊天时，用户被视作一个Agent，此时用户与Agent是平等的？

指令应该只包含文本，附件包含知识

知识不仅可以为其他模态的信息，也可以是纯文本


### 2. Msg需要承载的信息
Agent接收的信息：
指令：what to do：
	1. 来自用户的指令
	2. 
知识：what to know：
	2. 内部知识
		1. 文本记忆
		2. NDN数据包
	3. 外部知识
		1. 工具返回的知识：对于这些知识，直接给Agent使用，然后由Agent决定是否需要NDN入库。

Agent发出的信息：
知识：
	1. 日志
	2. 产出的知识（需要入库）
	3. 交付的结果
	4. 请求知识（向用户或另一Agent）

### 3. Msg不承载的信息
1. Agent内部的工作流
2. function call

### 4. Msg的核心结构
核心结构包含两个字段：
1. instruction / report：str
2. attachment / product：list

将Msg分为Instruction Msg和Result Msg：
User -> Agent: Instruction Msg
Agent -> Agent: Instruction Msg
Agent -> External Env: function call
External Env -> Agent: Result Msg
Agent -> Agent: Result Msg
Agent -> User Result Msg

instruction:
当消息为一对一时，instruction为单一字符串，表示指令。
当消息为一对多时，instruction为一个字典，key为指令，value为接收该指令的对象list

attachment:
用于存储执行instruction所需要的任意知识，包括：
	1. NDN数据包的name
	2. 传统的多模态信息
	3. 其他Msg
	4. 文本/json

report：
通过文本向上游单位报告

product：
当Result Msg被创建时，其包含的product总是新鲜且未入库的。product：
	1. 价值高：在使用完后入库转为NDN文件
	2. 价值低：不进行入库