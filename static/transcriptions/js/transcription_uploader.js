/*jshint esversion: 6 */
transcript_uploader = (function() {

  //public
  var prepareForm;

  //private
  var readFile, validateFile, showValidationReport, handleError, showErrorBox,
  indexFile, showProgress, setupAjax, csrfSafeMethod, getCookie;

  $(document).ready(function() {
    transcript_uploader.prepareForm();
  });

  prepareForm = function() {
    api.setupAjax();
    if (document.getElementById('transcription_upload_form')) {
      document.getElementById('index_button').disabled = true;
      document.getElementById('check_ingested_data').disabled = true;
      document.getElementById('transcription_upload_form').reset();
      document.getElementById('transcription_validate_form').reset();
      $('#index_file').off('change.load_index_file');
      $('#index_file').on('change.load_index_file', function() {
        readFile('index_file', 'src', function() {
          document.getElementById('index_button').disabled = false;
          $('#index_button').off('click.index');
          $('#index_button').on('click.index', function() {
            indexFile();
          });
        });
      });
    }
    document.getElementById('validate_button').disabled = true;
    $('#validation_file').off('change.load_validation_file');
    $('#validation_file').on('change.load_validation_file', function() {
      readFile('validation_file', 'validate_src', function() {
        document.getElementById('validate_button').disabled = false;
        $('#validate_button').off('click.validate');
        $('#validate_button').on('click.validate', function() {
          var f, options;
          f = document.getElementById('validation_file').files[0];
          options = forms.serialiseForm('transcription_validate_form');
          prepareForm();
          validateFile(options.validate_src, escape(f.name));
        });
      });
    });
    $('#download_schema_button').off('click');
    $('#download_schema_button').on('click', function () {
        window.location.href = '/transcriptions/schema';
    });
    $('#delete_transcription_button').off('click');
    $('#delete_transcription_button').on('click', function() {
      deleteFile();
    });
  };


  showErrorBox = function(report) {
    var error_div;
    if (document.getElementById('error') !== null) {
      document.getElementsByTagName('body')[0].removeChild(document.getElementById('error'));
    }
    error_div = document.createElement('div');
    error_div.setAttribute('id', 'error');
    error_div.setAttribute('class', 'error_message');
    error_div.innerHTML = '<span id="error_title"><b>Error</b></span>' +
                          '<div id="error_close">close</div><br/><br/>' + report;
    document.getElementsByTagName('body')[0].appendChild(error_div);
    $('#error_close').off('click.error-close');
    $('#error_close').on('click.error-close', function(event) {
      document.getElementsByTagName('body')[0].removeChild(document.getElementById('error'));
      window.location.reload();
    });
  };

  showMessageBox = function(report) {
    var message_div;
    if (document.getElementById('error') !== null) {
      document.getElementsByTagName('body')[0].removeChild(document.getElementById('error'));
    }
    message_div = document.createElement('div');
    message_div.setAttribute('id', 'error');
    message_div.setAttribute('class', 'message');
    message_div.innerHTML = '<span id="message_title"><b>Message</b></span>' +
                          '<div id="error_close">close</div><br/><br/>' + report;
    document.getElementsByTagName('body')[0].appendChild(message_div);
    $('#error_close').off('click.error-close');
    $('#error_close').on('click.error-close', function(event) {
      document.getElementsByTagName('body')[0].removeChild(document.getElementById('error'));
      window.location.reload();
    });
  };

  showProgressBox = function(data) {
    var message_div;
    data = JSON.parse(data);
    $('#check_ingested_data').off('click');
    $('#check_ingested_data').on('click', function() {
      window.location.href = '/transcriptions/collationunits/?siglum=' + data.siglum;
    });
    if (document.getElementById('error') !== null) {
      document.getElementsByTagName('body')[0].removeChild(document.getElementById('error'));
    }
    message_div = document.createElement('div');
    message_div.setAttribute('id', 'error');
    message_div.setAttribute('class', 'message');
    message_div.innerHTML = '<span id="message_title"><b>Indexing Progress</b></span>' +
                          '<div id="error_close"></div><br/><br/>' +
                          '<input type="hidden" id="task_id" value="' + data.task_id + '"/>' +
  		                    '<input type="hidden" id="siglum" value="' + data.siglum + '"/>' +
                          '<p id="message">Checking the server for the task.</p>' +
  		                    '<p id="indicator"></p>';
    document.getElementsByTagName('body')[0].appendChild(message_div);
  };

  handleError = function(action, error_report, model) {
    var report;
    report = 'An error has occurred.<br/>';
    if (error_report.status === 401) {
      report += '<br/>You are not authorised to upload transcriptions into the database.<br/>' +
        				'Please contact the server administrator.';
    } else if (error_report.status === 403) {
			if (error_report.responseText == 'work does not match project') {
				report += '<br/>You need to select the correct project for the transcription you are uploading.<br/>' +
	        				'Please select a different project and try again.';
			} else if (error_report.responseText == 'project is not public') {
				report += '<br/>You cannot upload a transcription with the public flag unless the project select is also public.<br/>' +
	        				'Please select a different project or choose the private option and try again.';
			} else {
				report += '<br/>You are not authorised to upload transcriptions into the database.<br/>' +
	        				'Please contact the server administrator.';
			}
    } else if (error_report.status === 415) {
      report += '<br/>It is has not been possible to process your request because ' +
        				error_report.responseText + '.';
    } else {
      report += '<br/>The server has encountered an error. Please try again. <br/>' +
        				'If the problem persists please contact the server administrator.';
    }
    showErrorBox(report);
  };

  showValidationReport = function(report) {
    if (!report.hasOwnProperty('valid')) {
        showMessageBox(report.filename + ' is being validated.');
        return;
    }
    if (report.valid === true) {
      showMessageBox(report.filename + ' is valid');
    } else {
      showErrorBox(report.filename + ' is not valid for the following reasons:<br/><br/>' +
        report.errors.join('<br/><br/>'));
    }
  };

  validateFile = function(string, file_name) {
    var options, url, callback;
    url = 'validate/';
    options = {
      'src': string,
      'file_name': file_name
    };
    showValidationReport(JSON.stringify({'file_name': file_name}));
    callback = function(resp) {
      showValidationReport(resp);
    };
    $.post(url, options, function(response) {
      callback(response);
    }, "json").fail(function(response) {
      prepareForm();
      handleError('validate', response);
    });
  };

  readFile = function(file_input_id, store_location_id, onload_callback) {
    var store_elem, input_file, reader;
    store_elem = document.getElementById(store_location_id);
    input_file = document.getElementById(file_input_id).files[0];
    reader = new FileReader();
    reader.onloadend = function() {
      store_elem.value = reader.result;
      if (onload_callback) {
        onload_callback();
      }
    };
    if (input_file) {
      reader.readAsDataURL(input_file);
    } else {
      store_elem.value = '';
    }
  };

  indexFile = function () {
    var data, indexing_url, callback, transcription_id;
    data = forms.serialiseForm('transcription_upload_form');
    showProgressBox(JSON.stringify({}));
    $('#index_button').off('click.index');
    $('#index_button').prop('disabled', true);
    if (data.skip_schema === 'on') {
      data.skip_schema = true;
    } else {
      delete data.skip_schema;
    }
    indexing_url = 'index/';
    callback = function (resp) {
      showProgressBox(resp);
      indexing.pollApparatusState();
    };
    $.post(indexing_url, data, function(response) {
      callback(response);
    }, "text").fail(function (response) {
      prepareForm();
      handleError('upload', response);
    });
  };

  deleteFile = function () {
    var ok, transcriptionDetails;
    transcriptionDetails = document.getElementById('delete-transcription').value;
    if (transcriptionDetails === 'none') {
      return;
    }
    ok = confirm('You are about to delete the transcription ' + transcriptionDetails.split('|')[0] + '.\nAre you sure you want to continue?');
    if (ok === true) {
      document.getElementById('transcription_delete_form').submit();
    } else {
      return;
    }
  };

  return {
    prepareForm: prepareForm
  };

}());
