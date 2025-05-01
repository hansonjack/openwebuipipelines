from typing import List, Union, Generator, Iterator, Optional
from pprint import pprint
import requests
import json
import warnings

class Pipeline:
    def __init__(self):
        self.name = "Coze Enhanced Pipeline"
        self.api_url = "https://api.coze.cn/open_api/v2/chat"
        self.api_key = "Bearer your_api_token"  # 替换为实际Token
        self.bot_id = "your_bot_id"             # 替换为实际Bot ID
        self.api_request_stream = False
        self.verify_ssl = True
        self.debug = True
    
    async def on_startup(self):
        """服务启动初始化"""
        if self.debug:
            print(f"🟢 {self.name} initialized")
    
    async def on_shutdown(self):
        """服务关闭清理"""
        if self.debug:
            print(f"🔴 {self.name} shutdown")

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """请求预处理"""
        if self.debug:
            print("\n🔷 Inlet Input:")
            pprint({"user_message": body.get("message"), "user": user})
        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """响应后处理"""
        if self.debug:
            print("\n🔶 Outlet Output:")
            pprint({"response": body, "user": user})
        return body

    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> Union[str, Generator, Iterator]:
        """核心处理逻辑"""
        # 准备请求
        headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        payload = {
            "bot_id": self.bot_id,
            "user": body.get("user", {}).get("id", "anonymous"),
            "query": user_message,
            "conversation_id": body.get("conversation_id", "default"),
            "stream": self.api_request_stream
        }

        try:
            # 发送请求
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                stream=self.api_request_stream,
                verify=self.verify_ssl,
                timeout=30
            )

            # 流式处理
            if self.api_request_stream:
                def generate_stream():
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line.decode('utf-8'))
                                yield self._parse_stream_chunk(chunk)
                            except Exception as e:
                                yield f"🚨 Error: {str(e)}"
                return generate_stream()

            # 非流式处理
            return self._parse_blocking_response(response)

        except requests.exceptions.RequestException as e:
            return f"🚨 请求失败: {str(e)}"
        except Exception as e:
            return f"🚨 处理错误: {str(e)}"

    def _parse_blocking_response(self, response: requests.Response) -> str:
        """解析非流式响应"""
        try:
            response_data = response.json()
            if self.debug:
                print("\n🔷 Raw API Response:")
                pprint(response_data)

            if response_data.get("code") != 0:
                return f"🚨 API错误: {response_data.get('msg', '未知错误')}"

            # 结构化解析
            result = {
                "answer": "",
                "images": [],
                "follow_ups": [],
                "debug_data": response_data if self.debug else None
            }

            for msg in response_data.get("messages", []):
                msg_type = msg.get("type")
                content = msg.get("content", "")

                # 主要回答
                if msg_type == "answer":
                    result["answer"] = content
                
                # 图片处理
                elif msg_type == "tool_response":
                    image_urls = self._extract_image_urls(content)
                    result["images"].extend(image_urls)
                
                # 后续问题
                elif msg_type == "follow_up":
                    result["follow_ups"].append(content)

            # 构建Markdown响应
            return self._build_markdown_response(result)

        except json.JSONDecodeError:
            return "🚨 无效的API响应格式"

    def _extract_image_urls(self, content: str) -> List[str]:
        """从tool_response提取图片URL"""
        try:
            tool_data = json.loads(content)
            return tool_data.get("data", {}).get("data", {}).get("image_urls", [])
        except:
            return []

    def _build_markdown_response(self, result: dict) -> str:
        """构建Markdown格式响应"""
        response = result["answer"]

        # 添加图片
        if result["images"]:
            response += "\n\n🖼️ **生成的图片**\n"
            response += "\n".join(
                [f'![图片]({url} "生成图片")' for url in result["images"]]
            )

        # 添加后续问题
        if result["follow_ups"]:
            response += "\n\n💡 **您可能还想问**\n"
            response += "\n".join(
                [f'- {q}' for q in result["follow_ups"]]
            )

        # 添加调试信息
        if self.debug and result["debug_data"]:
            response += "\n\n🔍 **调试信息**\n"
            response += f"```json\n{json.dumps(result['debug_data'], indent=2, ensure_ascii=False)}\n```"

        return response

    def _parse_stream_chunk(self, chunk: dict) -> str:
        """解析流式响应块"""
        if chunk.get("code") != 0:
            return f"🚨 流式错误: {chunk.get('msg')}"

        for msg in chunk.get("messages", []):
            if msg.get("type") == "answer":
                return msg.get("content", "")
        return ""

# # 使用示例
# if __name__ == "__main__":
#     # 初始化管道
#     pipeline = Pipeline()
#     pipeline.debug = True

#     # 模拟请求数据
#     test_body = {
#         "user": {"id": "test_user", "email": "user@example.com"},
#         "conversation_id": "test_conv_001"
#     }

#     # 测试非流式
#     print("🔷 测试非流式响应:")
#     response = pipeline.pipe(
#         user_message="生成春天森林的鲜花图片",
#         model_id="coze-bot",
#         messages=[],
#         body=test_body
#     )
#     print(response)

#     # 测试流式
#     print("\n🔷 测试流式响应:")
#     pipeline.api_request_stream = True
#     stream = pipeline.pipe(
#         user_message="讲一个关于森林的故事",
#         model_id="coze-bot",
#         messages=[],
#         body=test_body
#     )
#     for chunk in stream:
#         print(chunk, end="", flush=True)