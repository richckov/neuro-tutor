from openai import OpenAI


client = OpenAI(
    api_key="sk-46AlDd6efckrjHomV4x9meiCtZe57mYF",
    base_url="https://api.proxyapi.ru/openai/v1"
)

# Получаем список ассистентов
assistants = client.beta.assistants.list()

# Выводим ID и имена всех ассистентов
for assistant in assistants.data:
    print(f"ID: {assistant.id}, Name: {assistant.name}")
