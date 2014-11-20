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
                get_banner(show_id, function (banner) {
                    $('#downloads').append('<img src=' + banner + ' />');
                    $('#downloads').append('<p>'+download['progress']+'</p>');
                });
            });
        });
    };

    refresh();
    setInterval(refresh, 5000);
});
