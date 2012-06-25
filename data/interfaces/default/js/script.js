function getThumb(imgElem,id,type) {
	
	if ( type == 'artist' ) {
		var thumbURL = "getThumb?ArtistID=" + id;
	} else {
		var thumbURL = "getThumb?AlbumID=" + id;
	}
	// Get Data from the cache by Artist ID 	
	$.ajax({
		url: thumbURL,
		success: function(data){
			if ( data == "" ) {
				var imageUrl = "interfaces/default/images/no-cover-artist.png";
			}
			else {
				var imageUrl = data;
				}
			$(imgElem).attr("src",imageUrl).hide().fadeIn();
			$(imgElem).wrap('<a href="'+ imageLarge +'" rel="dialog" title="' + name + '"></a>');
			}
	});
}

function getArtwork(imgElem,id,type) {
	
	if ( type == 'artist' ) {
		var artworkURL = "getArtwork?ArtistID=" + id;
	} else {
		var artworkURL = "getArtwork?AlbumID=" + id;
	}
	// Get Data from the cache by Artist ID 	
	$.ajax({
		url: artworkURL,
		success: function(data){
			if ( data == "" ) {
				var imageUrl = "interfaces/default/images/no-cover-artist.png";
			}
			else {
				var imageUrl = data;
				}
			$(imgElem).attr("src",imageUrl).removeAttr("width").removeAttr("height").hide().fadeIn();
			$(imgElem).wrap('<a href="'+ imageLarge +'" rel="dialog" title="' + name + '"></a>');
			}
	});
}

function getInfo(elem,id,type) {
	
	if ( type == 'artist' ) {
		var infoURL = "getInfo?ArtistID=" + id;
	} else {
		var infoURL = "getInfo?AlbumID=" + id;
	}
	// Get Data from the cache by ID 	
	$.ajax({
		url: infoURL,
		dataType: "json",
		success: function(data){
			var summary = data.Summary;
			$(elem).append(summary);
		}
	});
}

function getImageLinks(elem,id,type) {
	
	if ( type == 'artist' ) {
		var infoURL = "getImageLinks?ArtistID=" + id;
	} else {
		var infoURL = "getImageLinks?AlbumID=" + id;
	}
	// Get Data from the cache by ID 	
	$.ajax({
		url: infoURL,
		dataType: "json",
		success: function(data){
			var thumbnail = data.thumbnail;
			var artwork = data.artwork;
			
			$(elem).attr("src", thumbnail);
		}
	});
}

function getOriginalWidthOfImg(img_element) {
    var t = new Image();
    t.src = (img_element.getAttribute ? img_element.getAttribute("src") : false) || img_element.src;
    return t.width;
}

function replaceEmptyAlbum(elem,name) {
	var album = $(elem);
	var artist = name;
	var albumname;
	var apikey = "690e1ed3bc00bc91804cd8f7fe5ed6d4";
	// Loop through every album art and get the albums with no cover
	$(album).each(function(e){
		var dimensions = getOriginalWidthOfImg(this);
		var cover = $(this);
		var url;
		albumname = cover.closest("tr").find("#albumname a").text();
		if ( dimensions <= 1) {
			url = "http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key=" + apikey + "&artist="+ artist +"&album="+ albumname +"&format=json&callback=?";
			var imageUrl;
			$.getJSON(url, function(data, response) {
				if (data.album === undefined)  {
					imageUrl = "interfaces/default/images/no-cover-art.png";
				} else {
					imageUrl = data.album.image[3]['#text'];	
					imageLarge = data.album.image[4]['#text'];					
				// If Last.fm don't provide a cover then use standard
				}
				$(cover).error(function(){
					imageUrl = "interfaces/default/images/no-cover-art.png";
					$(this).hide().attr("src", imageUrl).show();
				})
				if ( imageUrl == "") {
					imageUrl = "interfaces/default/images/no-cover-art.png";
					$(this).hide().attr("src", imageUrl).show();
				}
				$(cover).hide().attr("src", imageUrl).show();
				$(cover).wrap('<a href="'+ imageLarge +'" rel="dialog" title="' + artist + " - " + albumname + '"></a>');
			});
		} 	
	});		
}

function initHeader() {		
	//settings
	var header = $("#container header");
	var fadeSpeed = 100, fadeTo = 0.5, topDistance = 20;
	var topbarME = function() { $(header).fadeTo(fadeSpeed,1); }, topbarML = function() { $(header).fadeTo(fadeSpeed,fadeTo); };
	var inside = false;
	//do
	$(window).scroll(function() {
		position = $(window).scrollTop();
		if(position > topDistance && !inside) {
			//add events
			topbarML();
			$(header).bind('mouseenter',topbarME);
			$(header).bind('mouseleave',topbarML);
			$("#toTop").fadeIn();
			inside = true;
		}
		else if (position < topDistance){
			topbarME();
			$(header).unbind('mouseenter',topbarME);
			$(header).unbind('mouseleave',topbarML);
			$("#toTop").fadeOut();
			inside = false;
		}
	});
	
}

function initConfigCheckbox(elem) {
	var config = $(elem).parent().next();	
	if ( $(elem).is(":checked") ) {
		config.show();
	} else {
		config.hide();
	}
	$(elem).click(function(){
		var config = $(this).parent().next();	
		if ( $(this).is(":checked") ) {
			config.slideDown();
		} else {
			config.slideUp();
		}
	});
}     
function initActions() {
	$("#subhead_menu #menu_link_refresh").button({ icons: { primary: "ui-icon-refresh" }  });
	$("#subhead_menu #menu_link_edit").button({ icons: { primary: "ui-icon-pencil" }  });
    $("#subhead_menu #menu_link_delete" ).button({ icons: { primary: "ui-icon-trash" } });
    $("#subhead_menu #menu_link_pauze").button({ icons: { primary: "ui-icon-pause"} });
    $("#subhead_menu #menu_link_resume").button({ icons: { primary: "ui-icon-play"} });
    $("#subhead_menu #menu_link_getextra").button({ icons: { primary: "ui-icon-plus"} });
    $("#subhead_menu #menu_link_removeextra").button({ icons: { primary: "ui-icon-minus" } });    
    $("#subhead_menu #menu_link_wanted" ).button({ icons: { primary: "ui-icon-heart" } });
    $("#subhead_menu #menu_link_check").button({ icons: { primary: "ui-icon-arrowrefresh-1-w"} });
    $("#subhead_menu #menu_link_skipped").button({ icons: { primary: "ui-icon-seek-end"} });
    $("#subhead_menu #menu_link_retry").button({ icons: { primary: "ui-icon-arrowrefresh-1-e"} });
    $("#subhead_menu #menu_link_new").button({ icons: { primary: "ui-icon-arrowreturnthick-1-s" } });
    $("#subhead_menu #menu_link_shutdown").button({ icons: { primary: "ui-icon-power"} });
    $("#subhead_menu #menu_link_scan").button({ icons: { primary: "ui-icon-search"} });
}

function refreshSubmenu(url) {
	$("#subhead_container").load(url + " #subhead_menu",function(){
		initActions();
	});
}
function refreshTable() {
	var url =  $(location).attr('href');
	$("table.display").load(url + " table.display tbody, table.display thead", function() {
		initThisPage();
	});
}
function refreshLoadArtist() {
	if ( $(".gradeL").length > 0 ) {
		var url =  $(location).attr('href');
		var loadingRow = $("table.display tr.gradeL")
		loadingRow.each(function(){
			var row = $(this).index() + 1;
			var rowLoad = $("table.display tbody tr:nth-child("+row+")");
			$(rowLoad).load(url + " table.display tbody tr:nth-child("+ row +") td", function() {
				if ( $(rowLoad).children("#status").text() == 'Active'  ) {
					// Active
					$(rowLoad).removeClass('gradeL').addClass('gradeZ');
					initThisPage();
				} else {
					// Still loading
					setTimeout(function(){
						refreshLoadArtist();
					},3000);
				}
			});	
		});
	}
}

function refreshTab() {
	var url =  $(location).attr('href');
	var tabId = $('.ui-tabs-panel:visible').attr("id");
	$('.ui-tabs-panel:visible').load(url + " #"+ tabId, function() {
		initThisPage();
	});
}

function showMsg(msg,loader,timeout,ms) {
	var feedback = $("#ajaxMsg");
	update = $("#updatebar");
	if ( update.is(":visible") ) {
		var height = update.height() + 35;
		feedback.css("bottom",height + "px");
	} else {
		feedback.removeAttr("style");
	}
	feedback.fadeIn();
	var message = $("<div class='msg'>" + msg + "</div>");
	if (loader) {
		var message = $("<div class='msg'><img src='interfaces/default/images/loader_black.gif' alt='loading' class='loader' style='position: relative;top:10px;margin-top:-15px; margin-left:-10px;'/>" + msg + "</div>");
		feedback.css("padding","14px 10px")
	}
	$(feedback).prepend(message);
	if (timeout) {
		setTimeout(function(){
			message.fadeOut(function(){
				$(this).remove();
				feedback.fadeOut();					
			});
		},ms);
	} 
}

function doAjaxCall(url,elem,reload,form) {
	// Set Message
	feedback = $("#ajaxMsg");
	update = $("#updatebar");
	if ( update.is(":visible") ) {
		var height = update.height() + 35;
		feedback.css("bottom",height + "px");
	} else {
		feedback.removeAttr("style");
	}
	
	feedback.fadeIn();
	// Get Form data
	var formID = "#"+url;
	if ( form == true ) {
		var dataString = $(formID).serialize();
	}
	// Loader Image
	var loader = $("<img src='interfaces/default/images/loader_black.gif' alt='loading' class='loader'/>");
	// Data Success Message
	var dataSucces = $(elem).data('success');
	if (typeof dataSucces === "undefined") {
		// Standard Message when variable is not set
		var dataSucces = "Success!";
	} 
	// Data Errror Message
	var dataError = $(elem).data('error');
	if (typeof dataError === "undefined") {
		// Standard Message when variable is not set
		var dataError = "There was a error";
	} 	
	// Get Success & Error message from inline data, else use standard message
	var succesMsg = $("<div class='msg'><span class='ui-icon ui-icon-check'></span>" + dataSucces + "</div>");
	var errorMsg = $("<div class='msg'><span class='ui-icon ui-icon-alert'></span>" + dataError + "</div>");
	
	// Check if checkbox is selected
	if ( form ) {
		if ( $('td#select input[type=checkbox]').length > 0 && !$('td#select input[type=checkbox]').is(':checked') || $('#importLastFM #username:visible').length > 0 && $("#importLastFM #username" ).val().length === 0 ) {
			feedback.addClass('error')
			$(feedback).prepend(errorMsg);
			setTimeout(function(){
				errorMsg.fadeOut(function(){
					$(this).remove();
					feedback.fadeOut(function(){
						feedback.removeClass('error');
					});					
				})
				$(formID + " select").children('option[disabled=disabled]').attr('selected','selected');
			},2000);
			return false;
		} 
	} 
	
	// Ajax Call
	$.ajax({
	  url: url,
	  data: dataString,
	  beforeSend: function(jqXHR, settings) {
	  	// Start loader etc.
	  	feedback.prepend(loader);
	  },
	  error: function(jqXHR, textStatus, errorThrown)  {
	  	feedback.addClass('error')
	  	feedback.prepend(errorMsg);
	  	setTimeout(function(){
	  		errorMsg.fadeOut(function(){
	  			$(this).remove();
	  			feedback.fadeOut(function(){
	  				feedback.removeClass('error')
	  			});	  			
	  		})
	  	},2000);
	  },
	  success: function(data,jqXHR) {
	  	feedback.prepend(succesMsg);
	  	feedback.addClass('success')
	  	setTimeout(function(e){
	  		succesMsg.fadeOut(function(){
	  			$(this).remove();
	  			feedback.fadeOut(function(){
	  				feedback.removeClass('success');
	  			});
	  			if ( reload == true ) 	refreshSubmenu(url);
	  			if ( reload == "table") {
	  				console.log('refresh'); refreshTable();
	  			}
	  			if ( reload == "tabs") 	refreshTab();
	  			if ( form ) {
	  				// Change the option to 'choose...'
	  				$(formID + " select").children('option[disabled=disabled]').attr('selected','selected');
	  			}
	  		})
	  	},2000);
	  },
	  complete: function(jqXHR, textStatus) {
	  	// Remove loaders and stuff, ajax request is complete!
	  	loader.remove();
	  }
	});
}

function resetFilters(text){
	if ( $(".dataTables_filter").length > 0 ) {
		$(".dataTables_filter input").attr("placeholder","filter " + text + "");
	}
}

function preventDefault(){
	$("a[href='#']").live('click', function(){
		return false;
	});
}

function initFancybox() {
	if ( $("a[rel=dialog]").length > 0 ) {
		$.getScript('interfaces/default/js/fancybox/jquery.fancybox-1.3.4.js', function() {
			$("head").append("<link rel='stylesheet' href='interfaces/default/js/fancybox/jquery.fancybox-1.3.4.css'>");
	 		$("a[rel=dialog]").fancybox();
	 	});
	 }
}

function init() {
	initHeader();
	preventDefault();
}

$(document).ready(function(){
	init();
});
