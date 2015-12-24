'use strict';

/**
 * @ngdoc function
 * @name jittv2App.controller:SuggestionCtrl
 * @description
 * # SuggestionCtrl
 * Controller of the jittv2App
 */
angular.module('jittv2App')
  .controller('AppResourcesController', ["Jitt", "LocaleNames", "$routeParams",
  function (Jitt, localeNames, $routeParams) {
      var thiz = this;

      this.apikey = $routeParams.apikey;
      this.app = Jitt.MyApps.get({apikey: this.apikey});

      this.files = [];
      this.locales = [];
      this.num = 0;
      var ABRIDGED_PARTS = ["main","res","src","values"];
      this.parseFiles = function(data) {
          thiz.files = _.map(
                            _.sortBy(
                                _.filter(
                                         _.pairs(data.files),
                                         function(x) { return x[0][0] !== "$"; }
                                     ),
                                function(x) { return x[0]; }
                            ),
                            function(p) {
                                var fullpath = p[0];
                                var parts = fullpath.split('/');
                                var filename = parts[parts.length-1];
                                var pathlen = fullpath.length;
                                var abridgedpath = fullpath.substring(0,pathlen-filename.length);
                                for ( var _a = 0 ; _a < ABRIDGED_PARTS.length ; _a++ ) {
                                    abridgedpath = abridgedpath.replace(ABRIDGED_PARTS[_a],"&hellip;");
                                }
                                abridgedpath = abridgedpath.replace(/(\/&hellip;)+/g,"/&hellip;");
                                return {
                                    filename:filename,
                                    abridgedpath:abridgedpath,
                                    fullpath:p[0],
                                    num:p[1].num,
                                    locales:p[1].locales};
                                }
                            );
          thiz.locales =
            _.sortBy(
                _.filter(
                    _.map(
                        _.pairs(data.locales),
                        function(p) { return {name:p[0],num:p[1],engname:localeNames(p[0])}; }
                    ),
                    function(o) { return o.engname; }
                ),
             "engname");
          if ( thiz.locales.length > 0 ) {
            thiz.selectedLocale = _.filter(thiz.locales,function(l) {return l.name==='iw';});
            thiz.selectedLocale = thiz.selectedLocale.length > 0 ? thiz.selectedLocale[0] : thiz.locales[0];
          }
          thiz.num = data.num;
          if ( thiz.files.length > 0 ) {
              thiz.selectFile(thiz.files[0]);
          }
      };
      Jitt.Files.get({apikey: this.apikey}).$promise
                .then(this.parseFiles);

      this.selectedFile = null;
      this.selectedFileResources = null;
      this.selectFile = function(file){
          thiz.selectedFile = null;
          thiz.selectedFileResources = null;
          if ( file === null ) {
              return;
          }
          thiz.selectedFile = file;
          if ( thiz.selectedLocale === null ) {
              Jitt.Resources.query({apikey:thiz.apikey,locale:"_", filename:file.fullpath}).$promise
                            .then(thiz.parseResources);
          } else {
              Jitt.Resources.query({apikey:thiz.apikey,locale:thiz.selectedLocale.name,filename:file.fullpath}).$promise
                            .then(thiz.parseResources);
          }
      };

      this.parseResources = function(data) {
          thiz.selectedFileResources = data;
          thiz.selectedFileResources = _.sortBy(thiz.selectedFileResources, 'resource_id');
          for ( var _i = 0 ; _i < thiz.selectedFileResources.length ; _i++ ) {
              var res = thiz.selectedFileResources[_i];
              res.verified = false;
              for ( var _s = 0 ; _s < res.suggestions.length ; _s++ ) {
                  if ( res.suggestions[_s].score > 5 ) {
                      res.verified = true;
                      break;
                  }
              }
          }
          thiz.selectedResource = thiz.selectedFileResources[0];
      };

      this.selectedLocale = null;
      this.setLocale = function(locale) {
          thiz.selectedLocale = locale;
          thiz.selectFile(thiz.selectedFile);
      };

      this.selectedResource = null;
      this.selectResource = function(res) {
          thiz.selectedResource = res;
      };

      this.selectedSuggestion = null;
      this.selectSuggestion = function(sugg) {
          thiz.selectedSuggestion = sugg;
      };

      this.delete = function() {
          if ( thiz.selectedResource !== null ) {
              Jitt.Resource.delete({apikey:thiz.app.apikey,resource_id:thiz.selectedResource.resource_id}).$promise
                         .then(function() {
                             thiz.selectedFileResources =
                                _.filter(thiz.selectedFileResources,
                                         function(x) { return x.resource_id !== thiz.selectedResource.resource_id; });
                             thiz.selectResource(null);
                             $('#deleteResourceModal').modal('hide');
                         });
          }
      };

      this.deleteSuggestion = function() {
          if ( thiz.selectedResource !== null && thiz.selectedSuggestion !== null ) {
              Jitt.Resource.delete({apikey:thiz.app.apikey,
                                    resource_id:thiz.selectedResource.resource_id,
                                    locale:thiz.selectedLocale.name,
                                    suggestion:JSON.stringify(thiz.selectedSuggestion.text)
                                  }).$promise
                         .then(function() {
                             thiz.selectedResource.suggestions =
                                _.filter(thiz.selectedResource.suggestions,
                                         function(x) { return x.text !== thiz.selectedSuggestion.text; });
                             thiz.selectSuggestion(null);
                             $('#deleteSuggestionModal').modal('hide');
                         });
          }
      };

  }]);
