from flask import Flask, request, make_response

app = Flask('nab')
app.debug = True


def run():
    app.run()


@app.route('/')
def hello():
    return 'Hello World!'


@app.route('/log')
def log():
    response = make_response(file('log.txt').read())
    response.headers['content-type'] = 'text/plain'
    return response


@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        with file('config.yaml', 'w') as f:
            f.write(request.data)

    with file('config.yaml', 'r') as f:
        response = make_response(f.read())
        response.headers['content-type'] = 'text/yaml'
        return response


if __name__ == "__main__":
    run()
