import os
from dotenv import load_dotenv
from openai import OpenAI

class PMASController:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        
        # The Polyglot Model Mapping
        self.models = {
            "dependency": "google/gemini-2.5-flash",
            "navigation": "meta-llama/llama-3.3-70b-instruct",
            "analysis": "deepseek/deepseek-v3.2"
        }

    def query_agent(self, agent_role, system_prompt, user_content):
        response = self.client.chat.completions.create(
            model=self.models[agent_role],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"},
            max_tokens=4000
        )
        return response.choices[0].message.content
