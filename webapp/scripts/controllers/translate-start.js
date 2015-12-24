'use strict';

/**
 * @ngdoc function
 * @name jittv2App.controller:MainCtrl
 * @description
 * # MainCtrl
 * Controller of the jittv2App
 */
angular.module('jittv2App')
  .controller('TranslateStartController', ['$window', '$location', 'TranslationState', 'Jitt', 'LocaleNames',
  function ($window, $location, TranslationState, Jitt, localeNames) {
      var thiz = this;

      this.localeNames = localeNames;
      this.app = Jitt.Verification.get({apikey: TranslationState.apikey, token: TranslationState.token, userid: TranslationState.userid});
      this.locale = TranslationState.locale;
      this.userid = TranslationState.userid;

      $window.ga('send', 'event', 'translate', 'start', TranslationState.apikey);
      this.app.$promise.then( function(data) {
          document.title = "Translate "+data.name+" to "+thiz.localeNames(thiz.locale);
          $location.path('translate');
      });
  }]);
