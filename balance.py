import requests

from const import OPENAI_API_KEY


url = 'https://api.proxyapi.ru/proxyapi/balance'


def take_balance() -> str:
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    response = requests.get(url=url, headers=headers)
    try:
        if response.status_code == 200:
            data = response.json()
            balance = data["balance"]
            return balance
    except Exception as e:
        return f'Ошибка: {e}.'
    except requests.exceptions.RequestException as e:
        return f'Неожиданная ошибка: {e}'


def checking_balance() -> str:
    try:
        float_balance = (float(take_balance()))
        if float_balance < 200:
            return f'Кончается баланс: {float_balance}'
        else:
            return take_balance()
    except Exception as e:
        return f'Ошибка: {e}'
