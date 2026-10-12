from __future__ import annotations
from .config import settings

class LLMClient:
    def __init__(self, provider: str = "openai", model: str | None = None, api_key: str | None = None):
        self.provider = provider
        self.model = model or ("gpt-4o-mini" if provider=="openai" else "gemini-1.5-flash" if provider=="gemini" else "llama3.1")
        self.api_key = api_key

    def complete(self, prompt: str) -> str:
        if self.provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key or settings.OPENAI_API_KEY)
            r = client.chat.completions.create(model=self.model, messages=[{"role":"system","content":"Be concise."},{"role":"user","content":prompt}], temperature=0.2)
            return r.choices[0].message.content
        if self.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=self.api_key or settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(self.model)
            return model.generate_content(prompt).text
        if self.provider == "ollama":
            import requests
            base = settings.OLLAMA_BASE_URL or "http://127.0.0.1:11434"
            r = requests.post(f"{base}/api/chat", json={"model": self.model, "messages":[{"role":"user","content":prompt}]}, timeout=120)
            r.raise_for_status()
            data = r.json()
            return data.get("message",{}).get("content","(no content)")
        if self.provider == "grok":
            import requests
            headers = {"Authorization": f"Bearer {self.api_key or settings.XAI_API_KEY}"}
            body = {"model": self.model or "grok-2-latest", "messages":[{"role":"user","content":prompt}]}
            r = requests.post("https://api.x.ai/v1/chat/completions", json=body, headers=headers, timeout=120)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
        raise ValueError("Unknown provider")

def draft_email_reply(context: str, provider: str="openai") -> str:
    return LLMClient(provider=provider).complete(f"Draft a friendly professional email reply in <=120 words. Context:\n{context}")

def draft_proposal(context: str, provider: str="openai") -> str:
    return LLMClient(provider=provider).complete(f"Outline a concise project proposal with 3 milestones and bullet points. Context:\n{context}")

def run_chain(task: str, provider: str = "openai") -> str:
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        prompt = ChatPromptTemplate.from_template("You are a helpful assistant. Perform the task succinctly. Task: {task}")
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
        chain = prompt | llm | StrOutputParser()
        return chain.invoke({"task": task})
    except Exception:
        return LLMClient(provider=provider).complete(f"Perform the task succinctly:\n{task}")
