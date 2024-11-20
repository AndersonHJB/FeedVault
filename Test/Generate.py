import os
base_root = '/Users/huangjiabao/GitHub/Github_Repo/FeedVault'



def generate_text(paths, model='w'):
    text = ''
    for path in paths:
        filename = path.split('/')[-1]
        # with open(base_root + path, 'r') as f:
        with open(os.path.join(base_root, path), 'r') as f:
            content = f.read()
            text += filename + ':\n' + content + '\n'
    with open('data/text.txt', model) as f:
        f.write(text)

if __name__ == '__main__':
    data_dict = {
        'app': [
            "app.py",
            "config.py",
        ],
        'index': [
            "templates/index.html",
            "static/index.css"
        ],
        'admin': [
            'templates/admin.html',
            'static/admin.css',
        ],
        'login': [
            'templates/login.html',
            'templates/user_login.html',
            'static/login.css',
        ],
        'subscription': [
            'templates/subscription.html',
            'static/subscription.css',
        ],
        'other': [
            'static/base.css',
        ],
    }
    for paths in data_dict.values():
        # print(path)
        generate_text(paths, model='a+')

    # generate_text(data_dict['admin'], model='w')