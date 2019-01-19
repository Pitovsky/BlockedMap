$("#select_all").change(function() { 
    $(":checkbox.org").prop('checked', $(this).prop("checked"));
});

$(':checkbox.org').change(function(){ 
    if(false == $(this).prop("checked")) {
        $("#select_all").prop('checked', false);
    }
    if ($(':checkbox.org:checked').length == $(':checkbox.org').length) {
      $("#select_all").prop('checked', true);
    }
});

$(function() {
    var start = moment('2012-01-01');
    var end = moment();

    function cb(start, end) {
        $('#reportrange input').val(start.format('DD.MM.YYYY') + ' - ' + end.format('DD.MM.YYYY'));
    }

    moment.locale('en');
    $('#reportrange').daterangepicker({
        "locale": {
          "format": "DD.MM.YYYY",
          "separator": " - ",
          "firstDay": 1
        },
        startDate: start,
        endDate: end,
        ranges: {
           // 'Сегодня': [moment(), moment()],
           'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
           'Last week': [moment().subtract(6, 'days'), moment()],
           'Last month': [moment().subtract(1, 'months'), moment()],
           'Last year': [moment().subtract(12, 'months'), moment()]
        }
    }, cb);

    cb(start, end);
    
});


$(document).ready(function() {
    $(":checkbox.org").prop('checked', true);
    $("#submitform").submit();
});
