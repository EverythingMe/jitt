'use strict';

/**
 * @ngdoc function
 * @name jittv2App.controller:SuggestionCtrl
 * @description
 * # SuggestionCtrl
 * Controller of the jittv2App
 */
angular.module('jittv2App')
  .controller('AppUsersController', ["Jitt", "LocaleNames", "$routeParams",
  function (Jitt, localeNames, $routeParams) {
      var thiz = this;

      this.apikey = $routeParams.apikey;
      this.app = Jitt.MyApps.get({apikey: this.apikey});
      this.users = Jitt.Users.query({apikey: this.apikey});
      this.orderby = 'userid';

      this.setOrder = function(field) {
          thiz.orderby = field;
      };
    //   Jitt.Users.get({apikey: this.apikey}).$promise
    //             .then(this.parseUsers);
      //
    //   this.parseUsers = function(data) {
    //       thiz.users = data;
    //   };

      this.selectedLocale = null;
      this.setLocale = function(locale) {
          thiz.selectedLocale = locale;
          thiz.selectFile(thiz.selectedFile);
      };

      this.selectedUser = null;
      this.selectUser = function(user) {
          thiz.selectedUser = user;
      };

      this.timestr = function(timestamp) {
          return new Date(timestamp*1000).toLocaleString();
      };
  }]);
