from flask import Flask

app = Flask(__name__)
count = 0

@app.route('/')
def hello():
    global count
    count += 1
    return 'Hello World! I have been seen {} times.\n'.format(count)

