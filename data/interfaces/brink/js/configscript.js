
$(document).ready(function() { 
	// Ajax Config Form
    $('.ajax').ajaxForm({ 
        success: function() {
			var noty_id = noty({
				text:'<span class="wsr Approved"></span> Settings Saved!',
				layout: 'bottomRight',
				type:'success'
			});
			/*
			var noty_id = noty({
				text:'<span class="wsr Alert"></span>Carefull!',
				layout: 'bottomRight',
				type:'warning'
			});
			var noty_id = noty({
				text:'<span class="wsr Alert"></span> Something went wrong!',
				layout: 'bottomRight',
				type:'error'
			});
			var noty_id = noty({
				text:'<span class="wsr"></span> Settings has been saved successfully!',
				layout: 'bottomRight',
				type:'information'
			});
			var noty_id = noty({
				text:'<span class="wsr Approved"></span> Settings has been saved successfully!',
				layout: 'bottomRight',
				type:'success'
			});
			var noty_id = noty({
				text:'<span class="wsr Chat"></span> Settings has been saved successfully!',
				layout: 'bottomRight',
			});
			*/
        } 
    }); 
});

// Enabled/disabled label
$(document).ready(function(){
	$( '.switch' ).each(function(){
		//set Label name to current active state
		var labelName = 'label[for="' + $( this ).attr( "name" ) + '"]';
		var switchId = $( this ).attr( "name" ) + "_switch";
		if ( $( this ).is(':checked') ){
			$( labelName ).text( 'Enabled' );
			$("#" + switchId ).slideDown();
			enit();
		}
		else {
			$( labelName ).text( 'Disabled' );
			$("#" + switchId ).slideUp();
			enit();
		}
		//Change label
		$( this ).change(function(){
			if ( $( this ).is( ':checked' ) ){
				
				$( labelName ).text( 'Enabled' );
				$("#" + switchId ).slideDown();
				enit();
			}
			else{
				$( labelName ).text( 'Disabled' );
				$("#" + switchId ).slideUp();
				enit();
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
		if (a == 60){
			$('#' + sliderName ).text( (a-c)/b + " hour" );
		}
		else if (c <= 0){
			$('#' + sliderName ).text( (a-c)/b + " hours" );
		} else if ( a >= b ){
			$('#' + sliderName ).text( (a-c)/b + " hours " + c + " minutes" );
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
				if (a == 60){
					$('input[name="' + sliderName + '"]').val( ui.value );
					$('#' + sliderName ).text( (a-c)/b + " hour" );
				}
				else if (c <= 0){
					$('input[name="' + sliderName + '"]').val( ui.value );
					$('#' + sliderName ).text( (a-c)/b + " hours" );
				} else if ( a >= b ){
					$('input[name="' + sliderName + '"]').val( ui.value );
					$('#' + sliderName ).text( (a-c)/b + " hours " + c + " minutes" );
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