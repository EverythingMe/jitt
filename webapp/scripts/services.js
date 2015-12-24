'use strict';

var jittServices = angular.module('jittServices', ['ngResource']);

// var BASE = "http://localhost:12080";
//var BASE = "http://jitt-v2.appspot.com";
var BASE="";//http://jitt.io";

jittServices.factory('Jitt', ['$resource',
  function($resource){
      return {
            Base: BASE,
            Translate: $resource(BASE+'/api/translate', {userid:'@userid',apikey:'@apikey',token:'@token',locale:'@locale'}, {
                            translations: {method:'GET', params:{amount:5}, isArray:false, responseType:'json'},
                            update: {method:'POST', params:{votes:'@votes'}, isArray:false, responseType:'json'},
                        }),
            Login: $resource(BASE+'/api/admin/login', {next:'@next'}),
            MyApps: $resource(BASE+'/api/admin/app/:apikey',{apikey:'@apikey'}),
            AppStats: $resource(BASE+'/api/admin/stats/:apikey/:period',{apikey:'@apikey',period:'@period'}),
            TranslationStatus: $resource(BASE+'/api/admin/status/:apikey',{apikey:'@apikey'}),
            Files: $resource(BASE+'/api/admin/files/:apikey/:locale/:filename',{apikey:'@apikey'}),
            Resource: $resource(BASE+'/api/admin/resource/:apikey/:resource_id/:locale/:suggestion',
                                 {apikey:'@apikey',resource_id:'@resource_id',locale:'@locale',suggestion:'@suggestion'}),
            Resources: $resource(BASE+'/api/admin/resources/:apikey/:locale/:filename',
                                 {apikey:'@apikey',locale:'@locale',filename:'@filename'}),
            Users: $resource(BASE+'/api/admin/users/:apikey',{apikey:'@apikey'}),
            Verification: $resource(BASE+'/api/verification',{apikey:'@apikey',token:'@token',userid:'@userid'})
      };
}]);

jittServices.factory('LocaleNames', ['$window',
  function($window) {
      var thiz = this;
      this.languages = $window.LOCALE_NAMES;
      this.countries = $window.COUNTRY_NAMES;
    //   $http.get('locales.json').then(function(resp){thiz.map = resp.data;});
      return function(locale) {
          if ( locale===null ) { return null; }
          var parts = locale.split("-");
          if ( parts.length === 1 ) {
              return thiz.languages[parts[0]];
          } else {
              var country = parts[1].substring(1);
              if ( thiz.countries.hasOwnProperty(country) ) {
                    country = thiz.countries[country];
              }
              return thiz.languages[parts[0]]+" ("+country+")";
          }
      };
}]);

jittServices.factory('TranslationState', ['$routeParams', 'localStorageService',
  function($routeParams, LocalStorageService) {
      if ( $routeParams.apikey ) { LocalStorageService.set('apikey',$routeParams.apikey); }
      if ( $routeParams.locale ) { LocalStorageService.set('locale',$routeParams.locale); }
      if ( $routeParams.userid ) { LocalStorageService.set('userid',$routeParams.userid); }
      if ( $routeParams.token )  { LocalStorageService.set('token',$routeParams.token);  }
      return {
          apikey: LocalStorageService.get('apikey'),
          locale: LocalStorageService.get('locale'),
          userid: LocalStorageService.get('userid'),
          token:  LocalStorageService.get('token')
      };
  }]);
