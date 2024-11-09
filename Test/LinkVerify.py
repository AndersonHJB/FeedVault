import requests

def response(url: str) -> str:
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return "链接失效"


if __name__ == '__main__':
    url = 'http://127.0.0.1:5000/lUXKMGmSg8.yml'
    res = response(url)
    print(res)



