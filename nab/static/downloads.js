/*global $, document, $SCRIPT_ROOT*/
"use strict";

$(document).ready(function () {

    var downloads = {}, shows = {},
        format_bytes, add_download, remove_missing_shows, refresh;

    $('#downloads').accordion({
        collapsible: true,
        heightStyle: "content",
        active: false,
        icons: false
    });

    format_bytes = function (num) {
        var powers = ['bytes', 'KB', 'MB', 'GB', 'TB'], i = 0;
        while (num >= 1024 && i < powers.length) {
            num /= 1024;
            i += 1;
        }
        return num.toFixed(1) + powers[i];
    };

    function Show(id) {
        this.downloads = {};
        this.header = $('<h3 class="show-banner">');
        this.div = $('<div>');
        $('#downloads').append(this.header);
        $('#downloads').append(this.div);

        // retune the accordion
        $('#downloads').accordion("refresh");

        this.set_data = function (data) {
            this.data = data;

            // create banner for this show
            var banner = $('<img src="' + data.banner + '"/>');
            this.header.append(banner);
        };

        $.getJSON($SCRIPT_ROOT + '/shows/' + id, this.set_data.bind(this));

        this.add_download = function (download) {
            if (!this.downloads.hasOwnProperty(download.data.url)) {
                this.downloads[download.data.url] = download;
                this.div.append(download.div);
            }
        };

        this.delete = function () {
            this.header.remove();
            this.div.remove();
        };
    }

    function Download(data) {
        // add progress bar
        this.div = $('<div class=download><table><tr>');
        var that = this;

        (function () {
            var row = that.div.find('tr');
            row.append('<td class=filename>');
            row.append('<td class=size>');
            row.append('<td class=speed>');
            row.append('<td class=peers>');
        }());

        this.set_data = function (data) {
            this.data = data;
            this.div.find('.filename').text(data.filename);
            this.div.find('.size').text(format_bytes(data.size));
            this.div.find('.speed').text(format_bytes(data.downspeed) + '/s');
            this.div.find('.peers').text(data.num_seeds + "/" + data.num_peers);
            this.div.progressbar({value: data.progress * 100});
        };

        this.set_data(data);
    }

    add_download = function (down_data) {
        // find show on page
        var show_id = down_data.entry[0];
        if (!shows.hasOwnProperty(show_id)) {
            shows[show_id] = new Show(show_id);
        }

        // find download on page
        if (!downloads.hasOwnProperty(down_data.url)) {
            downloads[down_data.url] = new Download(down_data);
        }

        // Set download progress
        downloads[down_data.url].set_data(down_data);

        // Add download to matching show
        shows[show_id].add_download(downloads[down_data.url]);
    };

    remove_missing_shows = function (show_ids) {
        // Remove any shows on page if not in list of show_ids
        var show_id;
        for (show_id in shows) {
            if (shows.hasOwnProperty(show_id)) {
                if (show_ids.indexOf(show_id) === -1) {
                    shows[show_id].delete();
                    delete shows[show_id];
                }
            }
        }
    };

    refresh = function () {
        // Get download information
        $.getJSON($SCRIPT_ROOT + '/downloads', function (data) {
            data.forEach(add_download);

            remove_missing_shows(data.map(function (download) {
                return download.entry[0];
            }));
        });
    };

    refresh();
    setInterval(refresh, 5000);
});
