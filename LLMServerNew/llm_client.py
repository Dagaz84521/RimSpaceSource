# llm_client.py
import json
from openai import OpenAI
import requests # 假设使用标准 requests 调用，或者你可以用 openai 库
from config import LLM_API_KEY, LLM_MODEL, LLM_URL

class LLMClient:
    def __init__(self):
        self.api_key = LLM_API_KEY
        self.model = LLM_MODEL
        self.url = LLM_URL
        
    def query(self, system_prompt, user_context):
        """向 LLM 发送请求，获取响应"""
        client = OpenAI(
            base_url= self.url,
            api_key= self.api_key
        )
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_context}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content

    def parse_json_response(self, response_str):
        """尝试解析 LLM 返回的 JSON"""
        try:
            # 清理可能的 Markdown 标记 (```json ... ```)
            cleaned = response_str.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception as e:
            print(f"[LLM Error] 解析失败: {e}")
            return {"thought": "Error parsing", "command": "Wait", "target": ""}