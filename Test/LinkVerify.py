import requests

def response(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return "链接失效"


if __name__ == '__main__':
    url = 'http://127.0.0.1:5000/subscription/lUXKMGmSg8.yml'
    # url = 'http://127.0.0.1:5000/subscription/Ye2GGeKryX.yml'
    # url = 'http://127.0.0.1:5000/n6YKqu9f5a.yml'
    # url = 'http://127.0.0.1:5000/subscription'
    res = response(url)
    print(res)



