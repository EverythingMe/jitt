'use strict';

/**
 * @ngdoc overview
 * @name jittv2App
 * @description
 * # jittv2App
 *
 * Main module of the application.
 */
var app = angular
  .module('jittv2App', [
    //'ngAnimate',
    'ngCookies',
    'ngMessages',
    'ngResource',
    'ngRoute',
    'ngSanitize',
    'ngTouch',
    'LocalStorageModule',
    'jittServices'
  ])
  .config(function ($routeProvider) {
    $routeProvider
      .when('/start/:apikey/:locale/:token/:userid', {
        templateUrl: 'views/translate-start.html',
        controller: 'TranslateStartController',
        controllerAs: 'start'
      })
      .when('/translate', {
        templateUrl: 'views/translate.html',
        controller: 'TranslateController',
        controllerAs: 'translate'
      })
      .when('/thanks/:more', {
        templateUrl: 'views/translate-done.html',
        controller: 'TranslateDoneController',
        controllerAs: 'done'
      })
      .when('/my-apps', {
        templateUrl: 'views/my-apps.html',
        controller: 'MyAppsController',
        controllerAs: 'myapps'
      })
      .when('/resources/:apikey', {
        templateUrl: 'views/app-res.html',
        controller: 'AppResourcesController',
        controllerAs: 'appres'
      })
      .when('/users/:apikey', {
        templateUrl: 'views/app-users.html',
        controller: 'AppUsersController',
        controllerAs: 'appusers'
      })
      .when('/status/:apikey', {
        templateUrl: 'views/app-status.html',
        controller: 'AppStatusController',
        controllerAs: 'appstatus'
      })
      .when('/', {
        templateUrl: 'views/main.html',
        controller: 'MainController',
        controllerAs: 'main'
      })
      .otherwise({
        redirectTo: '/'
      });
  });
  app.run(["$rootScope", "$location", function ($rootScope, $location) {
      $rootScope.$on('$routeChangeSuccess', function(){
          ga('send', 'pageview', $location.path());
      });
  }]);
