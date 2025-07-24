from typing import List, Optional
from Module.RAG.RAGManager import RAGManager, ChatMessage

from Module.LLM.LLMProxy import LLMProxy

class ChatMessageMerger:
    def __init__(self, rag: RAGManager, llm_proxy: LLMProxy):
        self.rag = rag
        self.llm_proxy = llm_proxy

    async def summary_messages_daily(self, messages: List[ChatMessage]):
        """
        对消息进行摘要处理，使用 RAGManager 进行向量化和存储。
        :param messages: 要处理的聊天消息列表
        """
        if not messages:
            print("No messages to summarize.")
            return
    
        # 对当天的聊天消息进行总结
        # 提取消息内容
        msgs = [msg.content for msg in messages]
        res = await self.llm_proxy.summary_chat_message(msgs, summary_type="daily")
        
        return res
    