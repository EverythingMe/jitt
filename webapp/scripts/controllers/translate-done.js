'use strict';

/**
 * @ngdoc function
 * @name jittv2App.controller:DoneController
 * @description
 * # DoneController
 * Controller of the jittv2App
 */
angular.module('jittv2App')
  .controller('TranslateDoneController', ["$location", "TranslationState", "$routeParams",
  function ($location, TranslationState, $routeParams) {
      this.more = $routeParams.more !== 'false';

      if (ga) { ga('send', 'event', 'translate', 'done', TranslationState.apikey); }

      this.moreClicked = function() {
          if (ga) { ga('send', 'event', 'translate', 'more', TranslationState.apikey); }
          $location.path('translate');
      };
  }]);
