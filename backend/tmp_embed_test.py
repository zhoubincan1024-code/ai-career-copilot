"""临时测试：embedding 模型可用性与维度"""
import sys

sys.path.insert(0, r"C:\Users\zhoub\Desktop\AI 求职助手\ai-career-copilot\backend")

from openai import OpenAI

from app.core.config import settings

client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

for model in ["doubao-embedding-text-240715", "doubao-embedding-large-text-240915", "doubao-embedding-text-240515"]:
    try:
        r = client.embeddings.create(model=model, input=["测试文本", "第二个句子"])
        dim = len(r.data[0].embedding)
        print(f"OK  {model}  dim={dim}  count={len(r.data)}")
    except Exception as e:
        print(f"ERR {model}: {str(e)[:120]}")
