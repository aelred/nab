/*global $, _, Backbone, document, $SCRIPT_ROOT*/

$(document).ready(function () {
    'use strict';

    var format_bytes = function (num) {
        var powers = ['bytes', 'KB', 'MB', 'GB', 'TB'], i = 0;
        while (num >= 1024 && i < powers.length) {
            num /= 1024;
            i += 1;
        }
        return num.toFixed(1) + powers[i];
    };

    var Download = Backbone.Model.extend({
        parse: function (response) {
            response.size = format_bytes(response.size);
            response.downspeed = format_bytes(response.downspeed) + '/s';
            return response;
        }
    });

    var DownloadCollection = Backbone.Collection.extend({
        model: Download,
        url: $SCRIPT_ROOT + '/downloads'
    });

    var downloads = new DownloadCollection();

    downloads.fetch();
    setInterval(function () {
        downloads.fetch();
    }, 5000);

    var Show = Backbone.Model.extend({
        urlRoot: $SCRIPT_ROOT + '/shows',
        defaults: {
            banner: ""
        },

        initialize: function () {
            this.fetch();
        }
    });

    var ShowCollection = Backbone.Collection.extend({
        model: Show,
        url: $SCRIPT_ROOT + '/shows'
    });
    
    var DownloadView = Backbone.View.extend({
        template: _.template($('#download').html()),

        initialize: function () {
            this.listenTo(this.model, 'change', this.render);
            this.listenTo(this.model, 'destroy', this.remove);
        },

        render: function () {
            this.$el.html(this.template(this.model.toJSON()));
            this.$('.download').progressbar({
                value: this.model.get('progress') * 100
            });
            return this;
        }
    });

    var ShowView = Backbone.View.extend({
        template: _.template($('#show-banner').html()),
        
        initialize: function () {
            this.$el.accordion({
                collapsible: true,
                heightStyle: 'content',
                active: false,
                icons: false
            });
            this.download_views = [];
            this.listenTo(this.model, 'change', this.render);
            this.listenTo(this.model, 'destroy', this.remove);
        },

        render: function () {
            this.$el.html(this.template(this.model.toJSON()));
            var that = this;
            _.each(this.download_views, function(view) {
                that.$('.show-downloads').append(view.render().$el);
            });
            this.$el.accordion('refresh');
            return this;
        },

        add_download: function (download) {
            var view = new DownloadView({model: download});
            this.download_views.push(view);
            return view;
        }
    });

    var AllDownloadsView = Backbone.View.extend({
        initialize: function () {
            this.show_views = {};
            this.listenTo(downloads, 'add', this.add_download);
            this.listenTo(downloads, 'reset', this.render);
        },

        add_download: function (download) {
            var show = new Show({id: download.get('show')});
            return this.add_show(show).add_download(download).render();
        },

        add_show: function (show) {
            if (!_.has(this.show_views, show.id)) {
                this.show_views[show.id] = new ShowView({model: show});
                this.$el.append(this.show_views[show.id].render().$el);
            };
            var view = this.show_views[show.id];
            view.render();
            return view;
        },
    });

    // declare globals
    nab.AllDownloadsView = AllDownloadsView
});
