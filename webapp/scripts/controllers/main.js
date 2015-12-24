'use strict';

/**
 * @ngdoc function
 * @name jittv2App.controller:SuggestionCtrl
 * @description
 * # SuggestionCtrl
 * Controller of the jittv2App
 */
angular.module('jittv2App')
  .controller('MainController', ['$scope', "Jitt", function ($scope, Jitt) {
    $scope.$parent.landing = true;
    this.base = Jitt.Base;
    this.login = Jitt.Login.get({next:'#/my-apps'});

    this.getstarted = function() {
        $('html, body').animate({
            scrollTop: $("[name='getstarted']").offset().top
        }, 1000);
    };
  }]);
