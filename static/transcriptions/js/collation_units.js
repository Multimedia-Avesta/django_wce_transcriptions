/*jshint esversion: 6 */
units = (function () {
    "use strict";

    $(document).ready(function() {
      $('.buttonlink').on('click', function(event){
          event.preventDefault();
          window.location = $(this).attr('data-url');
      });
    });

  } () );
