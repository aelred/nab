from flask import Flask, request, make_response
import yaml

import nab.config

app = Flask('nab')
# app.debug = True


def run():
    app.run()


@app.route('/log')
def log():
    response = make_response(file('log.txt').read())
    response.headers['content-type'] = 'text/plain'
    return response


@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        nab.config.change_config(yaml.safe_load(request.data))

    response = make_response(yaml.safe_dump(nab.config.config))
    response.headers['content-type'] = 'text/yaml'
    return response
