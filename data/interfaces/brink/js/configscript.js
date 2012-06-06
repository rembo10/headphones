
$(function(){
	$( ".tabs" ).tabs();
});

$(".save").click(function(){
	messageDialog("update", "Your settings has been saved!")
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

Event = function(){
	alert("hello");
}

$( "#api_enabled" ).change(Event(););

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