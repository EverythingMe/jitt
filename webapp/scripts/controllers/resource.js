'use strict';

/**
 * @ngdoc function
 * @name jittv2App.controller:SuggestionCtrl
 * @description
 * # SuggestionCtrl
 * Controller of the jittv2App
 */
angular.module('jittv2App')
  .controller('ResourceController', ["$scope", function ($scope) {
      var thiz = this;

      this.resource = $scope.res;
      this.translate = $scope.translate;
      this.context = this.resource.context;
      this.original = this.resource.original;
      this.res_id = this.resource.id;
      this.suggestions = this.resource.suggestions;

      this.clear = function() {
          thiz.resource.error = null;
          thiz.resource.voted = null;
          thiz.update();
      };

      this.vote = function(sugg) {
          thiz.clear();
          thiz.resource.voted = sugg;
          thiz.update();
      };

      this.suggest = function(sugg) {
          thiz.clear();
          thiz.resource.suggested = sugg;
          thiz.update();
      };

      this.unclear = function() {
          thiz.clear();
          thiz.resource.error = 'unclear';
          thiz.update();
      };

      this.skip = function() {
          thiz.clear();
          thiz.resource.error = 'skip';
          thiz.update();
      };

      this.update = function() {
          thiz.resource.own_suggestion = (thiz.resource.suggested !== null) && (thiz.resource.suggested.length > 0) && thiz.resource.voted === null && thiz.resource.error === null;
          thiz.translate.update();
      };

      this.clear();

  }]);
