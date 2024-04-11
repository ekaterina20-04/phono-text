import requests


def get_file_history(id):
    try:
        response = requests.get(f'http://127.0.0.1:5000/{id}/get_file_history')
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print('Ошибка при получении данных:', e)
        return None


id = input("Введите ID файла: ")
text_versions = get_file_history(id)
if text_versions:
    print('История файла:', text_versions)

