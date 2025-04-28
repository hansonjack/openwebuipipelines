from typing import List, Union, Generator, Iterator, Optional,Dict,Any
from pprint import pprint
import requests, json, warnings
from pydantic import BaseModel, Field
import os

# Uncomment to disable SSL verification warnings if needed.
# warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class Pipeline:
    class Valves(BaseModel):
        DIFY_API_KEY: str = Field(default="", description="FlowiseAI API key (from Bearer key, e.g. QMknVTFTB40Pk23n6KIVRgdB7va2o-Xlx73zEfpeOu0)")
        DIFY_BASE_URL: str = Field(default="", description="FlowiseAI base URL (e.g. http://localhost:3000 (URL before '/api/v1/prediction'))")
        params: Dict[str, Any] = Field(
        default_factory=dict,
        description="动态调用参数，支持：\n"
                    "- model: 模型名称 (默认: gpt-3.5-turbo)\n"
                    "- temperature: 采样温度 (范围: 0-2)\n"
                    "- max_tokens: 最大生成长度"
    )
    def __init__(self):
        self.name = "Dify Chat Flow"
        self.valves = self.Valves(
            **{k: os.getenv(k, v.default) for k, v in self.Valves.model_fields.items()}
        )
        self.api_url = "http://api:5001/v1/chat-messages"     # Set correct hostname
        self.api_key = "app-o5MH3KLA6l1wANi4oG4uU4OV"                              # Insert your actual API key here.v 
        self.api_request_stream = True                             # Dify support stream
        self.verify_ssl = False
        self.debug = True
    
    async def on_startup(self):
        # This function is called when the server is started.
        print(f"on_startup: {__name__}")
        pass
    
    async def on_shutdown(self): 
        # This function is called when the server is shutdown.
        print(f"on_shutdown: {__name__}")
        pass

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        # This function is called before the OpenAI API request is made. You can modify the form data before it is sent to the OpenAI API.
        print(f"inlet: {__name__}")
        if self.debug:
            print(f"inlet: {__name__} - body:")
            pprint(body)
            print(f"inlet: {__name__} - user:")
            pprint(user)
        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        # This function is called after the OpenAI API response is completed. You can modify the messages after they are received from the OpenAI API.
        print(f"outlet: {__name__}")
        if self.debug:
            print(f"outlet: {__name__} - body:")
            pprint(body)
            print(f"outlet: {__name__} - user:")
            pprint(user)
        return body

    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> Union[str, Generator, Iterator]:
        print(f"pipe: {__name__}")
        
        if self.debug:
            print(f"pipe: {__name__} - received message from user: {user_message}")

        # Set reponse mode Dify API parameter
        if self.api_request_stream is True:
            response_mode = "streaming"
        else:
            response_mode = "blocking"

        ## 获取chat_id
        chat_id = body.get('metadata').get('chat_id')
        if not chat_id:
            yield f"Workflow not get the chat_id"
        
        # This function triggers the workflow using the specified API.
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            "inputs": {"prompt": user_message},
            "query": user_message,
            "conversation_id": "",
            "user": "abc-123",
            "files": [],
            "response_mode": response_mode,
            "user": body["user"]["email"]
        }
        ### 根据chat_id 获取 dify_conversion_id 若获取到则在请求参数中加上conversion_id,若没获取到，就不加。
        response = requests.post(self.api_url, headers=headers, json=data, stream=self.api_request_stream, verify=self.verify_ssl)
        print("哈哈哈哈哈哈哈哈哈哈哈")
        print(data)
        print("================================================")
        print(response.text)
        print("================================================")
        if response.status_code == 200:
            # Process and yield each chunk from the response
            for line in response.iter_lines():
                if line:
                    try:
                        # Remove 'data: ' prefix and parse JSON
                        json_data = json.loads(line.decode('utf-8').replace('data: ', ''))
                        # Extract and yield only the 'text' field from the nested 'data' object
                        if 'data' in json_data and 'text' in json_data['data']:
                            ###获取 dify 返回中的 dify_conversion_id
                            ###把chat_id和 dify_conversion_id 对应关系缓存起来。
                            yield json_data['data']['text']
                    except json.JSONDecodeError:
                        print(f"Failed to parse JSON: {line}")
        else:
            yield f"Workflow request failed with status code: {response.status_code}"