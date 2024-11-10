import os
base_root = '/Users/huangjiabao/GitHub/Github_Repo/FeedVault'



def generate_text(paths):
    text = ''
    for path in paths:
        filename = path.split('/')[-1]
        # with open(base_root + path, 'r') as f:
        with open(os.path.join(base_root, path), 'r') as f:
            content = f.read()
            text += filename + ':\n' + content + '\n'
    with open('data/text.txt', 'w') as f:
        f.write(text)

if __name__ == '__main__':
    paths = [
        'templates/admin.html',
        'templates/login.html',
        'templates/user_login.html',
        'templates/subscription.html',
        'static/style.css'
    ]
    generate_text(paths)