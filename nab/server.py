from flask import Flask, request, make_response, abort
import yaml
import json
import copy

from nab import config
from nab import downloader
from nab import log

app = Flask('nab')

_shows = None


def init(shows):
    global _shows
    _shows = shows


def run():
    app.run(debug=True, use_reloader=False)


@app.route('/log')
def log_():
    response = make_response(file(log.log_file).read())
    response.headers['content-type'] = 'text/plain'
    return response


@app.route('/config', methods=['GET', 'POST'])
def config_all():
    return get_config([])


@app.route('/config/<path:path>', methods=['GET', 'POST'])
def config_path(path=''):
    return get_config(path.split('/'))


@app.route('/remove/<path:path>', methods=['POST'])
def remove(path):
    path = path.split('/')
    plugin = request.values['plugin']
    conf_copy = copy.deepcopy(config.config)
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
    config.change_config(conf_copy)

    return config_response(conf_copy)


def get_config(path):
    # navigate provided path along config file
    conf_copy = copy.deepcopy(config.config)
    conf_sub = access_config_path(conf_copy, path)

    if request.method == 'POST':
        # replace config path with given data
        access_config_path(conf_copy, path, yaml.safe_load(request.data))
        # update config
        config.change_config(conf_copy)

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

    if path:
        return conf_sub[path[-1]]
    else:
        return config_data


@app.route('/downloads', methods=['GET'])
def downloads():
    download_data = []

    for (download, entry) in downloader.get_downloads().iteritems():
        download_data.append({
            'filename': download.filename,
            'url': download.url,
            'entry': entry.id
            })

    response = make_response(yaml.safe_dump(download_data))
    response.headers['content-type'] = 'text/yaml'
    return response


@app.route('/show/<path:path>', methods=['GET'])
def show(path):
    entry = _shows.find(tuple(path))

    if not entry:
        abort(204)

    response = make_response(yaml.safe_dump(entry.to_yaml()))
    response.headers['content-type'] = 'text/yaml'
    return response
