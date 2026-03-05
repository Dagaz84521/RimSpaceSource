from openai import OpenAI
import os, json, configs

client = OpenAI(
    api_key=configs.LLM_API_KEY,
    base_url=configs.LLM_URL
)

def call_model(messages, model=configs.LLM_MODEL, temperature=0.7, max_tokens=4096):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content, response.usage.total_tokens
