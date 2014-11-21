$(document).ready(function(){

    var get_banner = function(show_id, callback) {
        $.getJSON($SCRIPT_ROOT + '/show/' + show_id, function (data) {
            // extract banner
            callback(data['banner']);
        });
    };

    var refresh = function() {
        // Get download information
        $.getJSON($SCRIPT_ROOT + '/downloads', function (data) {
            // Clear display
            $('#downloads').html('');
            $.each(data, function(index, download) {
                // Add banner for this download
                var show_id = download['entry'][0];
                get_banner(show_id, function (banner_url) {
                    var banner = $('<img src=' + banner_url + ' />');
                    $('#downloads').append(banner);
                    progressJs(banner).start();
                    progressJs(banner).set(download['progress'] * 100);

                });
            });
        });
    };

    refresh();
    setInterval(refresh, 5000);
});
