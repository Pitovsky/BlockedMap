$("#select_all").change(function() { 
    $(":checkbox").prop('checked', $(this).prop("checked"));
});

$(':checkbox').change(function(){ 
    if(false == $(this).prop("checked")) {
        $("#select_all").prop('checked', false);
    }
    if ($(':checkbox:checked').length == $(':checkbox').length) {
      $("#select_all").prop('checked', true);
    }
});

$(function() {
    var start = moment('2012-01-01');
    var end = moment();

    function cb(start, end) {
        $('#reportrange input').val(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
    }

    $('#reportrange').daterangepicker({
        "locale": {
          "format": "MM/DD/YYYY",
          "separator": " - ",
          "applyLabel": "Применить",
          "cancelLabel": "Отмена",
          "customRangeLabel": "Другой период",
          "firstDay": 1
        },
        startDate: start,
        endDate: end,
        ranges: {
           // 'Сегодня': [moment(), moment()],
           'Вчера': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
           'За неделю': [moment().subtract(6, 'days'), moment()],
           'За месяц': [moment().subtract(1, 'months'), moment()],
           'За год': [moment().subtract(12, 'months'), moment()]
        }
    }, cb);

    cb(start, end);
    
});


$(document).ready(function() {
    $("#submitform").submit();
    $(":checkbox").prop('checked', true);
});
