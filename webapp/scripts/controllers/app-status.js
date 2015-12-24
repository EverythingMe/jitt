'use strict';

/**
 * @ngdoc function
 * @name jittv2App.controller:SuggestionCtrl
 * @description
 * # SuggestionCtrl
 * Controller of the jittv2App
 */
angular.module('jittv2App')
  .controller('AppStatusController', ["Jitt", "LocaleNames", "$routeParams",
  function (Jitt, LocaleNames, $routeParams) {
    //   var thiz = this;

      this.apikey = $routeParams.apikey;
      this.app = Jitt.MyApps.get({apikey: this.apikey});
      this.localeNames = LocaleNames;
      this.status = Jitt.TranslationStatus.query({apikey: this.apikey});

  }]);
