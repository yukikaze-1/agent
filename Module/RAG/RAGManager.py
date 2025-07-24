from calendar import c
import os

from typing import List, Dict, Tuple
from pymilvus import MilvusClient, DataType
from langchain.text_splitter import RecursiveCharacterTextSplitter
from Module.RAG.ChatMessage import ChatMessage, AttachmentFile, MessageAttachment
from Module.RAG.Utils import create_embedding_model, create_milvus_client


class EmbeddingChatMessageModel:
    def __init__(self, client: MilvusClient,
                 model: str = "BAAI/bge-large-en-v1.5",
                 collection_name: str = "chat_messages"):
        self.client = client
        self.collection_name = collection_name
        self.embedding_model = create_embedding_model(model=model)
        self.milvus_client = create_milvus_client(host="localhost", port=19530)

    async def embedding_chat_message(self, message: ChatMessage) -> Tuple[List[List[float]], List[List[float]]]:
        """
        嵌入对话消息
        """
        if not isinstance(message, ChatMessage):
            raise TypeError("Expected message to be an instance of ChatMessage")
        
        # Embedding the content of the chat message
        vectors_content = await self.embedding_texts([message.content])
        
        # Embedding the attatchments of the chat message
        if message.attachments is not None:
            print(f"Embedding attachments for message ID {message.message_id}")
            vector_attachments = await self.embedding_attatchments(message.attachments)
        else:
            vector_attachments = []
        return vectors_content, vector_attachments
    
    async def embedding_texts(self, texts: List[str]) -> List[List[float]]:
        """
        嵌入文本内容为向量列表
        """
        
        # 检查并分割过长的文本
        processed_texts = []
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        for text in texts:
            text = text.strip()
            if len(text) > 400:  # 根据模型调整阈值
                chunks = splitter.split_text(text)
                processed_texts.extend(chunks)
            else:
                processed_texts.append(text)
        
        # 批量处理，避免一次处理过多文档
        batch_size = 32
        all_vectors = []
        
        for i in range(0, len(processed_texts), batch_size):
            batch = processed_texts[i:i + batch_size]
            try:
                batch_vectors = await self.embedding_model.aembed_documents(batch)
                all_vectors.extend(batch_vectors)
            except Exception as e:
                print(f"Batch embedding failed: {e}")
                # 可以选择跳过或使用备用方案
                raise

        return all_vectors
    
    async def embedding_attatchment(self, file: AttachmentFile)-> List[List[float]]:
        """
        嵌入附件内容为向量列表
        """
        support_docs_type = [".pdf", ".docs", ".txt", ".md"]
        support_audio_type = [".mp3", ".wav",]
        support_image_type = [".jpg", ".png",]

        support_file_type = support_docs_type + support_audio_type + support_image_type

        if not file.is_valid():
            raise ValueError("Invalid attachment file")
        file_type = file.type()
        if file_type not in support_file_type:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        if file_type in support_docs_type:
            return await self.embedding_docs([str(file.file_path)], model="BAAI/bge-large-en-v1.5")
        elif file_type in support_audio_type:
            return await self.embedding_audio([str(file.file_path)], model="BAAI/bge-large-en-v1.5")
        elif file_type in support_image_type:
            return await self.embedding_image([str(file.file_path)], model="BAAI/bge-large-en-v1.5")
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    async def embedding_attatchments(self, attachments: MessageAttachment) -> List[List[float]]:
        """
        嵌入多个附件内容为向量列表
        """
        # 没有附件时返回空列表
        if attachments is None or not attachments.get_files():
            return []

        # 嵌入每个附件的内容
        vectors = []
        for file in attachments.get_files():
            vectors.append(await self.embedding_attatchment(file))
        return vectors

    async def embedding_docs(self, docs: List[str], model: str = "BAAI/bge-large-en-v1.5") -> List[List[float]]:
        """
        嵌入文档内容为向量列表
        """
        embedding_model = create_embedding_model(model=model)
        return await embedding_model.aembed_documents(docs)

    async def embedding_audio(self, audio_files: List[str], model: str = "BAAI/bge-large-en-v1.5") -> List[List[float]]:
        """
        嵌入音频内容为向量列表
        """
        embedding_model = create_embedding_model(model=model)
        # TODO 待修改
        return await embedding_model.aembed_documents(audio_files)

    async def embedding_image(self, image_files: List[str], model: str = "BAAI/bge-large-en-v1.5") -> List[List[float]]:
        """
        嵌入图像内容为向量列表
        """
        embedding_model = create_embedding_model(model=model)
        # TODO 待修改
        return await embedding_model.aembed_documents(image_files)
    
    async def query(self, query: str, top_k: int = 3) -> List[List[dict]]:
        """
        查询 Milvus 数据库
        """
        query_vector = await self.embedding_model.aembed_query(query)
        res = self.milvus_client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=top_k,
            output_fields=["role", "content", "timestamp", "message_id"],
        )
        return res



class RAGManager:
    def __init__(self, collection_name: str) -> None:
        self.collection_name = collection_name
        self.milvus_client = create_milvus_client(host="localhost", port=19530)
        self.embedding_model = EmbeddingChatMessageModel(client=self.milvus_client, collection_name=self.collection_name)

    async def messages_to_RAG(self, messages: List[ChatMessage], clear: bool = False ,model: str = "BAAI/bge-large-en-v1.5") -> bool:
        """
        将 ChatMessage 存入RAG系统
        """
        if not isinstance(messages, list) or not all(isinstance(msg, ChatMessage) for msg in messages):
            return False
        
        # 嵌入消息内容为向量
        vectors_content: List[List[float]] = []
        vector_attatchment: List[List[float]] = []
        
        for message in messages:
            if not isinstance(message, ChatMessage):
                raise TypeError("Expected message to be an instance of ChatMessage")
            
            # 嵌入消息内容
            vectors_content_msg, vector_attatchment_msg = await self.embedding_model.embedding_chat_message(message)
            vectors_content.append(vectors_content_msg[0])
            # vector_attatchment.append(vector_attatchment_msg[0])
            
        vector_dims = len(vectors_content[0])
        collection_name = "chat_messages"
        
        if clear:
            # 清空集合
            if self.milvus_client.has_collection(collection_name):
                self.milvus_client.drop_collection(collection_name)
            else:
                print(f"Collection {collection_name} does not exist, no need to clear.")

        # 检查并创建集合
        if not self.milvus_client.has_collection(collection_name):
            self.create_collection(collection_name, vector_dims)
            
        # 插入数据
        res = self.milvus_client.insert(
            collection_name=collection_name,
            data=[{
                    "role": message.role,
                    "content": message.content,
                    "vector": vector_content,
                    "timestamp": message.timestamp.isoformat(),
                    "message_id": message.message_id
                }for message, vector_content in zip(messages, vectors_content)
            ]
        )
        
        # 加载集合到内存（重要！）
        self.milvus_client.load_collection(collection_name)
        print(f"Collection {collection_name} loaded into memory.")

        # 打印插入结果
        print(f"Insert result: {res}")
        
        return True
    
    
    async def query(self, query: str, top_k: int = 3) -> List[List[dict]]:
         # 检查集合是否已加载，如果未加载则加载
        try:
            # 先尝试查询来检测是否已加载
            return await self.embedding_model.query(query=query, top_k=top_k)
        except Exception as e:
            if "collection not loaded" in str(e):
                print(f"Collection {self.collection_name} not loaded, loading now...")
                self.milvus_client.load_collection(self.collection_name)
                print(f"Collection {self.collection_name} loaded into memory.")
                # 重新尝试查询
                return await self.embedding_model.query(query=query, top_k=top_k)
            else:
                raise e
            
    def create_collection(self, collection_name: str, vector_dims: int):
        """
        创建 Milvus 集合,添加向量字段和索引
        """
        if not self.milvus_client.has_collection(collection_name):
            schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
            schema.add_field(field_name="role", datatype=DataType.VARCHAR, max_length=50)
            schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=5000)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=vector_dims)
            schema.add_field(field_name="timestamp", datatype=DataType.VARCHAR, max_length=50)
            schema.add_field(field_name="message_id", datatype=DataType.INT64, is_primary=True)
        
            self.milvus_client.create_collection(
                collection_name=collection_name,
                # dimension=vector_dims,
                schema=schema,
            )
            print(f"Collection {collection_name} created.")
            
            # 创建向量字段的索引（提高搜索性能）
            index_params = self.milvus_client.prepare_index_params()
            index_params.add_index(
                field_name="vector",
                index_type="IVF_FLAT",
                metric_type="COSINE",
                params={"nlist": 1024}
            )
            self.milvus_client.create_index(
                collection_name=collection_name,
                index_params=index_params
            )
            print(f"Index created for collection {collection_name}.")