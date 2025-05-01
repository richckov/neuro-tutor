from openai import OpenAI

from const import prompt


client = OpenAI(
    api_key="sk-46AlDd6efckrjHomV4x9meiCtZe57mYF",
    base_url="https://api.proxyapi.ru/openai/v1"
)


my_assistant = client.beta.assistants.create(
    instructions=prompt,
    name="Tutor with no MarkdownV2",
    # tools=[{"type": "code_interpreter"}],
    model="gpt-4o-mini",
)

print(my_assistant)
