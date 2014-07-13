from flask import Flask, request, make_response, abort
import yaml
import copy

import nab.config

app = Flask('nab')


def run():
    app.run(debug=True, use_reloader=False)


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


@app.route('/remove/<path:path>', methods=['POST'])
def remove(path):
    path = path.split('/')
    plugin = request.values['plugin']
    conf_copy = copy.deepcopy(nab.config.config)
    conf_sub = access_config_path(conf_copy, path)

    try:
        # search for plugin
        for i, p in enumerate(conf_sub):
            try:
                # test for:
                # - watching
                # or
                # - watching:
                #       params...
                if plugin == p or plugin in p.keys():
                    break
            except AttributeError:
                # this entry is not a dictionary, ignore
                pass
        index = i
    except AttributeError:
        # this is a dictionary
        index = plugin

    # delete plugin from config file
    del conf_sub[index]
    nab.config.change_config(conf_copy)

    return config_response(conf_copy)


def config(path):
    # navigate provided path along config file
    conf_copy = copy.deepcopy(nab.config.config)
    conf_sub = access_config_path(conf_copy, path)

    if request.method == 'POST':
        # replace config path with given data
        access_config_path(conf_copy, path, yaml.safe_load(request.data))
        # update config
        nab.config.change_config(conf_copy)

    return config_response(conf_sub)


def config_response(config_data):
    response = make_response(yaml.safe_dump(config_data))
    response.headers['content-type'] = 'text/yaml'
    return response


def access_config_path(config_data, path, config_set=None):
    conf_sub = config_data
    # navigate to second-from-last index, to allow referencing later
    for p in path[:-1]:
        conf_sub = conf_sub[p]

    if config_set is not None:
        conf_sub[path[-1]] = config_set
    return conf_sub[path[-1]]
