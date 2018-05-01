$("#select_all").change(function(){ 
    $(":checkbox").prop('checked', $(this).prop("checked")); //change all ".checkbox" checked status
});

$(':checkbox').change(function(){ 
    if(false == $(this).prop("checked")){ //if this item is unchecked
        $("#select_all").prop('checked', false); //change "select all" checked status to false
    }
    if ($(':checkbox:checked').length == $(':checkbox').length ){
      $("#select_all").prop('checked', true);
    }
});

$(function() {

    var start = moment().subtract(10, 'years');
    var end = moment();

    function cb(start, end) {
        $('#reportrange input').val(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
    }

    $('#reportrange').daterangepicker({
        startDate: start,
        endDate: end,
        ranges: {
           'Today': [moment(), moment()],
           'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
           'Last 7 Days': [moment().subtract(6, 'days'), moment()],
           'Last 30 Days': [moment().subtract(29, 'days'), moment()],
           'This Month': [moment().startOf('month'), moment().endOf('month')]
        }
    }, cb);

    cb(start, end);
    
});


$(document).ready(function(){
    $("#submitform").submit();
});
