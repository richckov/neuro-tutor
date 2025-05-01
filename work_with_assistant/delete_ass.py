from openai import OpenAI


client = OpenAI(
    api_key="sk-46AlDd6efckrjHomV4x9meiCtZe57mYF",
    base_url="https://api.proxyapi.ru/openai/v1"
)

assistants = client.beta.assistants.list()

for assistant in assistants.data:
    client.beta.assistants.delete(assistant.id)
    print(f"✅ Удалён: {assistant.id} - {assistant.name}")
