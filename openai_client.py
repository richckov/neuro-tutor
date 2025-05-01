import openai

from const import OPENAI_API_KEY

client = openai.OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.proxyapi.ru/openai/v1",
)
