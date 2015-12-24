'use strict';

/**
 * @ngdoc function
 * @name jittv2App.controller:SuggestionCtrl
 * @description
 * # SuggestionCtrl
 * Controller of the jittv2App
 */
angular.module('jittv2App')
  .controller('MyAppsController', ["Jitt", function (Jitt) {
      var thiz = this;

      this.myApps = null;
      this.selectedApp = null;
      this.stats = null;

      this.statPeriods = [
          { name: '1hr', longname: 'hour', value: 1 },
          { name: '6hrs', longname: '6 hours', value: 6 },
          { name: '1day', longname: 'day', value: 24 },
          { name: '7days', longname: 'week', value: 24*7 },
          { name: '1mon', longname: 'month', value: 24*30 }
      ];

      this.setStatPeriod = function(period) {
          thiz.period = period;
          if ( period !== null ) {
              thiz.stats = Jitt.AppStats.get({apikey:thiz.selectedApp.apikey,period:period.value});
          }
      };

      this.selectApp = function(app) {
          thiz.selectedApp = app;
          thiz.stats = null;
          thiz.saved = false;
          if ( thiz.selectedApp !== thiz.candidateApp ) {
              if ( thiz.myApps[thiz.myApps.length-1] === thiz.candidateApp  ) {
                  thiz.myApps.pop();
              }
              thiz.candidateApp = null;
              if ( app !== null ) {
                  thiz.setStatPeriod( thiz.statPeriods[3] );
              }
          }
      };

      this.candidateApp = null;
      this.addApp = function() {
          if ( thiz.candidateApp === null ) {
            thiz.candidateApp = {name: null};
            thiz.myApps.push(thiz.candidateApp);
            thiz.selectApp(thiz.candidateApp);
        }
      };

      this.saved = false;
      this.save = function() {
          if ( thiz.selectedApp !== null ) {
              Jitt.MyApps.save({apikey:thiz.selectedApp.apikey},thiz.selectedApp).$promise
                         .then(function(response) {
                             thiz.saved = true;
                             for ( var k in response) {
                                 if ( k[0] === '$' ) {
                                     continue;
                                 }
                                 thiz.selectedApp[k] = response[k];
                             }
                             thiz.candidateApp = null;
                         });

          }
      };
      this.delete = function() {
          if ( thiz.selectedApp !== null ) {
              Jitt.MyApps.delete({apikey:thiz.selectedApp.apikey}).$promise
                         .then(function() {
                             thiz.myApps = _.filter(thiz.myApps, function(x) { return x.apikey !== thiz.selectedApp.apikey; });
                             thiz.selectApp(null);
                             $('#deleteModal').modal('hide');
                         });
          }
      };

      this.fetchApps = function() {
          Jitt.MyApps.query().$promise
          .then( function(data) {
              thiz.myApps = data;
              if ( thiz.myApps.length > 0 ) {
                  thiz.selectApp(thiz.myApps[0]);
              }
          });
      };
      this.fetchApps();

  }]);
