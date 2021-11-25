/*jshint esversion: 6 */
indexing = (function () {
    "use strict";

    var pollApparatusState;
    var poll_xhr;


  pollApparatusState = function () {
    var poll, stop;
    stop = 0;
    poll = function(){
        var task_id, siglum;
        task_id = document.getElementById('task_id').value;
        siglum = document.getElementById('siglum').value;
        poll_xhr = $.ajax({
          url:'../pollstate',
          type: 'POST',
          data: {
              task_id: task_id,
          },
          success: function(result) {
              var message;
              if (result.state === 'SUCCESS' || result.state === 'FAILURE') {
                  stop = 1;
                  if (result.state === 'SUCCESS') {
                      document.getElementById('message').innerHTML = 'The indexing of ' + siglum + ' is complete.<br/><br/>If you want to check the data uploaded do so before closing this message.';
                      document.getElementById('indicator').innerHTML = '';
                      document.getElementById('check_ingested_data').disabled = false;

                  } else {
                      if (result.result.message !== undefined) {
                          message = result.result.message;
                      } else {
                          message = result.result;
                      }
                      document.getElementById('message').innerHTML = 'Your task failed with the message:<br/><br/>' +
                                                                     message + '<br/><br/>' +
                                                                     'Task Id: ' + task_id;
                      document.getElementById('indicator').innerHTML = '';
                  }
                  document.getElementById('error_close').innerHTML = 'close';
                  $('#error_close').off('click.error-close');
                  $('#error_close').on('click.error-close', function(event) {
                    document.getElementsByTagName('body')[0].removeChild(document.getElementById('error'));
                    window.location.reload();
                  });
              } else if (result.state === 'PENDING') {
                  // We have the flag to tell us when the task has started so pending is a waiting state
                  document.getElementById('message').innerHTML = 'Your task is waiting to start.' +
                                                                 '<br/><br/>Task Id: ' + task_id;
                  document.getElementById('indicator').innerHTML += '.&#8203;';
              } else {
                  document.getElementById('message').innerHTML = 'Indexing of ' + siglum +
                                                                 ' in progress.<br/><br/>Task Id: ' + task_id;
                  document.getElementById('indicator').innerHTML += '.&#8203;';
              }
          }
        });
    };
    var refreshIntervalId = setInterval(function() {
        poll();
        if(stop == 1){
            clearInterval(refreshIntervalId);
        }
    }, 500);
  };

  return {pollApparatusState: pollApparatusState};



} () );
