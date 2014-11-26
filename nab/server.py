from flask import Flask, request, abort, render_template, make_response
from flask.ext.holster.main import init_holster
import yaml
import copy

from nab import config
from nab import downloader
from nab import log

app = Flask('nab')
init_holster(app)

_shows = None


def init(shows):
    global _shows
    _shows = shows


def run():
    app.run(debug=True, use_reloader=False)


@app.route('/')
def index():
    return render_template('index.html', name='Felix')


@app.route('/log')
def log_():
    response = make_response(file(log.log_file).read())
    response.headers['content-type'] = 'text/plain'
    return response


@app.holster('/config', methods=['GET', 'POST'])
def config_all():
    return get_config([])


@app.holster('/config/<path:path>', methods=['GET', 'POST'])
def config_path(path=''):
    return get_config(path.split('/'))


@app.holster('/remove/<path:path>', methods=['POST'])
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
                # - following
                # or
                # - following:
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

    return conf_copy


def get_config(path):
    # navigate provided path along config file
    conf_copy = copy.deepcopy(config.config)
    conf_sub = access_config_path(conf_copy, path)

    if request.method == 'POST':
        # replace config path with given data
        access_config_path(conf_copy, path, yaml.safe_load(request.data))
        # update config
        config.change_config(conf_copy)

    return conf_sub


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


@app.holster('/downloads', methods=['GET'])
def downloads():
    download_data = []

    for (download, entry) in downloader.get_downloads().iteritems():
        download_data.append({
            'filename': download.filename,
            'size': downloader.get_size(download),
            'progress': downloader.get_progress(download),
            'downspeed': downloader.get_downspeed(download),
            'upspeed': downloader.get_upspeed(download),
            'num_seeds': downloader.get_num_seeds(download),
            'num_peers': downloader.get_num_peers(download),
            'url': download.url,
            'entry': entry.id
            })

    return download_data


@app.holster('/show/<path:path>', methods=['GET'])
def show(path):
    search = path.split('/')
    # everything after the show name is an integer (season/ep number)
    search[1:] = [int(s) for s in search[1:]]

    entry = _shows.find(tuple(search))

    if not entry:
        abort(204)

    return entry.to_yaml()
