from flask import Flask, request, make_response
import yaml
import copy

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
def config_all():
    return config([])


@app.route('/config/<path:path>', methods=['GET', 'POST'])
def config_path(path=''):
    return config(path.split('/'))


def config(path):
    # navigate provided path along config file
    conf_copy = copy.deepcopy(nab.config.config)
    conf_sub = conf_copy
    # navigate to second-from-last index, to allow referencing later
    for p in path[:-1]:
        conf_sub = conf_sub[p]

    response = make_response(yaml.safe_dump(conf_sub[path[-1]]))
    response.headers['content-type'] = 'text/yaml'

    if request.method == 'POST':
        # replace config path with given data
        # index used so change is made to conf_copy
        conf_sub[path[-1]] = yaml.safe_load(request.data)
        # update config
        nab.config.change_config(conf_copy)

    return response
