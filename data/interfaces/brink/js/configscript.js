
$(document).ready(function() { 
	// Ajax Config Form
    $('.ajax').ajaxForm({ 
        success: function() {
			var noty_id = noty({
				"text":"Settings has been saved successfully!",
				"type":"success"
			});
        } 
    }); 
});

// Enabled/disabled label
$(document).ready(function(){
	$( '.switch' ).each(function(){
		//set Label name to current active state
		var labelName = 'label[for="' + $(this).attr("name") + '"]';
		if ( $( this ).is(':checked') ){
			$( labelName ).text( 'Enabled' );
		}
		else {
			$( labelName ).text( 'Disabled' );
		}
		//Change label
		$( this ).change(function(){
			if ( $( this ).is( ':checked' ) ){
				
				$( labelName ).text( 'Enabled' );
			}
			else{
				$( labelName ).text( 'Disabled' );
			}
		});
	});
});


//Slider for interval
$(function(){
	$( '.sliderInterval' ).each(function(){
		var sliderName = $(this).attr("for");
		var a = $('input[name="' + sliderName + '"]').val();
		var b = 60;
		var c = a % b;
		if ( a >= b ){
			$('#' + sliderName ).text( (a-c)/b + " hour/s " + c + " minutes" );
		} else {
			$('#' + sliderName ).text( a + " minutes" );
		}
		// Slider Function
		$( this ).slider({
			range: "max",
			min: 30,
			max: 1440,
			step: 10,
			value: a,
			slide: function( event, ui ) {
				a = ui.value;
				c = a % b;
				if(a >= b){
					$('input[name="' + sliderName + '"]').val( ui.value );
					$('#' + sliderName ).text( (a-c)/b + " hour/s " + c + " minutes" );
				} else {
					$('input[name="' + sliderName + '"]').val( ui.value );
					$('#' + sliderName ).text( a + " minutes" );
				}
			}
		});
	});
});

// Sliders
$(document).ready(function() {
	var amountDwnld = $( "#amount-download-scan" ).val();
	$( "#slider-download-scan" ).slider({
		value: amountDwnld,
		min: 1,
		max: 120,
		slide: function( event, ui ) {
			$( "#amount-download-scan" ).val(ui.value);
		}
	});
});
$(function() {
	var amountSearch = $( "#amount-nbz-search" ).val();
	$( "#slider-nbz-search" ).slider({
		value: amountSearch,
		min: 1,
		max: 120,
		slide: function( event, ui ) {
			$( "#amount-nbz-search" ).val(ui.value);
		}
	});
});
$(function() {
	var amountLib = $( "#amount-lib-scan" ).val();
	$( "#slider-lib-scan" ).slider({
		value: amountLib,
		min: 1,
		max: 120,
		slide: function( event, ui ) {
			$( "#amount-lib-scan" ).val( ui.value );
		}
	});
});

hideServerDivs = function () {
	$("#customoptions").hide("fast");
	$("#hpserveroptions").hide("fast");
};
// end sliders

handleNewSelection = function () {

	hideServerDivs();
	
	switch ($(this).val()) {
		case 'custom':
			$("#customoptions").show("fast");
		break;
		case 'headphones':
			$("#hpserveroptions").show("fast");
		break;
	}
};

$( 'input[type="checkbox"]' ).change(function()
{
	if ($("#api_enabled").is(":checked"))
		{
			$("#apioptions").show();
		}
	else
		{
			$("#apioptions").hide();
		}
	
	$("#api_enabled").is(":checked", function(){
		$("#apioptions").show();
	});		

	$("#api_key").click(function(){ $("#api_key").select() });
	$("#generate_api").click(function(){
		$.get('generateAPI', 
			function(data){
				if (data.error != undefined) {
					alert(data.error);
					return;
				}
				$('#api_key').val(data);
		});
	});
	if ($("#encode").is(":checked"))
		{
			$("#encoderoptions").show();
		}
	else
		{
			$("#encoderoptions").hide();
		}

	$("#encode").click(function(){
		if ($("#encode").is(":checked"))
		{
			$("#encoderoptions").show("fast");
		}
		else
		{
			$("#encoderoptions").hide("fast");
		}
	});

	if ($("#prowl").is(":checked"))
		{
			$("#prowloptions").show();
		}
	else
		{
			$("#prowloptions").hide();
		}
	
	$("#prowl").click(function(){
		if ($("#prowl").is(":checked"))
		{
			$("#prowloptions").show("fast");
		}
		else
		{
			$("#prowloptions").hide("fast");
		}
	});		

	if ($("#xbmc").is(":checked"))
		{
			$("#xbmcoptions").show();
		}
	else
		{
			$("#xbmcoptions").hide();
		}
	
	$("#xbmc").click(function(){
		if ($("#xbmc").is(":checked"))
		{
			$("#xbmcoptions").show("fast");
		}
		else
		{
			$("#xbmcoptions").hide("fast");
		}
	});		
	
	if ($("#nma").is(":checked"))
		{
			$("#nmaoptions").show();
		}
	else
		{
			$("#nmaoptions").hide();
		}
	
	$("#nma").click(function(){
		if ($("#nma").is(":checked"))
		{
			$("#nmaoptions").show("fast");
		}
		else
		{
			$("#nmaoptions").hide("fast");
		}
	});	
	$("#mirror").change(handleNewSelection);
	handleNewSelection.apply($("#mirror"));

});