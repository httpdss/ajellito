function estimate_change() {
         // copy the value from remaining over to estimate
         if ($("#id_actuals").val() == 0)
                  $("#id_remaining").val($("#id_estimate").val());
}

$(window).load(function(){
        $("#id_estimate").change(estimate_change);
});
