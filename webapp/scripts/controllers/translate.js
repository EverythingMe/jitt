'use strict';

/**
 * @ngdoc function
 * @name jittv2App.controller:AboutCtrl
 * @description
 * # AboutCtrl
 * Controller of the jittv2App
 */
angular.module('jittv2App')
  .controller('TranslateController', ["$location", "Jitt", "TranslationState", "LocaleNames", function ($location,Jitt,TranslationState,LocaleNames) {
      var thiz = this;

      this.amount = 5;
      this.locale = TranslationState.locale;
      this.localeNames = LocaleNames;

      this.init = function() {
          thiz.resources = null;
          thiz.more = true;
          thiz.completed = 0;
          thiz.saved = false;

          Jitt.Translate.translations(
              {apikey: TranslationState.apikey,
               token: TranslationState.token,
               locale: TranslationState.locale,
               userid: TranslationState.userid,
               amount:thiz.amount}).$promise
             .then(function(data){
                 thiz.resources = data.resources;
                 thiz.more = data.more;
                 thiz.new_user = data.new_user;
                 thiz.amount = thiz.resources.length;
                 for ( var _r = 0 ; _r < thiz.amount ; _r++ ) {
                     thiz.resources[_r].suggested = null;
                     thiz.resources[_r].voted = null;
                     thiz.resources[_r].error = null;
                 }
                 if ( thiz.amount === 0 ) {
                     $location.path('thanks/'+thiz.more);
                 }
                 if (ga) { ga('send', 'event', 'translate', 'receive', TranslationState.apikey, thiz.amount); }
             });
      };
      this.init();

      this.restart = function() {
          if (ga) { ga('send', 'event', 'translate', 'more', TranslationState.apikey); }
          thiz.amount += 2;
          thiz.init();
      };

      this.save = function() {
          var votes = [];
          for ( var _resource = 0 ; _resource < this.resources.length ; _resource++ ) {
              var resource = this.resources[_resource];
              if (resource.suggested !== null && resource.suggested.length === 0) {
                  resource.suggested = null;
              }
              if (resource.suggested === null && resource.voted === null ) {
                  if ( resource.error === null ) {
                      resource.error = "skipped";
                  }
              }
              votes.push({
                  resource_id: resource.id,
                  error: resource.error,
                  text: resource.voted === null ? resource.suggested : resource.voted
              });
          }
          var payload = {
              apikey: TranslationState.apikey,
              token: TranslationState.token,
              locale: TranslationState.locale,
              userid: TranslationState.userid,
              votes: JSON.stringify(votes)
          };
          if (ga) { ga('send', 'event', 'translate', 'submit', TranslationState.apikey, thiz.amount); }
          Jitt.Translate.update(payload).$promise
              .then(function(success) {
                        if ( success ) {
                            if (ga) { ga('send', 'event', 'translate', 'saved', TranslationState.apikey, thiz.amount); }
                            if ( !thiz.more ) {
                                $location.path('thanks/'+thiz.more);
                            }
                            thiz.saved = true;
                        }
                    });
      };

      this.update = function() {
          thiz.completed = 0;
          for ( var _i = 0 ; _i<thiz.resources.length ; _i++ ) {
              var res = thiz.resources[_i];
              if ( res.voted === null && (res.suggested === null || res.suggested.length === 0 ) && res.error === null ) {
                  continue;
              }
              thiz.completed++;
          }
      };
  }]);
