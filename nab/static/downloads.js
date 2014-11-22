$(document).ready(function(){

    var downloads = {};
    var shows = {};

    $('#downloads').accordion({
        collapsible: true,
        heightStyle: "content",
        active: false,
        icons: false
    });

    function Show(id) {
        this.downloads = {};
        this.header = $('<h3 class="show-banner">');
        this.div = $('<div>');
        $('#downloads').append(this.header);
        $('#downloads').append(this.div);

        // retune the accordion
        $('#downloads').accordion("refresh");

        this.set_data = function(data) {
            this.data = data;

            // create banner for this show
            var banner = $('<img src="'+data.banner+'"/>');
            this.header.append(banner);
        };

        $.getJSON($SCRIPT_ROOT + '/show/' + id, this.set_data.bind(this));

        this.add_download = function(download) {
            if (!(download.data.url in this.downloads)) {
                this.downloads[download.data.url] = download;
                this.div.append(download.div);
            }
        };

        this.delete = function() {
            this.header.remove();
            this.div.remove();
        };
    }

    function Download(data) {
        // add progress bar
        this.div = $('<div class="download">');
        this.overlay = $('<div class="download-label">');
        this.div.append(this.overlay);

        this.set_data = function(data) {
            this.data = data;
            this.overlay.text(data.filename);
            this.div.progressbar({value: data.progress * 100});
        };

        this.set_data(data);

    }

    var refresh = function() {
        // Get download information
        $.getJSON($SCRIPT_ROOT + '/downloads', function (data) {

            var show_ids = data.map(function(download) {
                return download.entry[0];
            });

            data.forEach(function(data) {
                // find show on page
                var show_id = data.entry[0];
                if (!(show_id in shows)) {
                    shows[show_id] = new Show(show_id);
                }

                // find download on page
                var down_url = data.url;
                if (!(down_url in downloads)) {
                    downloads[down_url] = new Download(data);
                }

                // Set download progress
                downloads[down_url].set_data(data);

                // Add download to matching show
                shows[show_id].add_download(downloads[down_url]);
            });

            // Remove any downloads on page if not in data
            for (var show_id in shows) {
                if (show_ids.indexOf(show_id) === -1) {
                    shows[show_id].delete();
                    delete shows[show_id];
                }
            }
        });
    };

    refresh();
    setInterval(refresh, 5000);
});
