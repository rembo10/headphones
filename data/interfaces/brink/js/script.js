function getArtistInfo(name,imgElem,size,artistID) {
	var apikey = "690e1ed3bc00bc91804cd8f7fe5ed6d4";
	
	// Get Data by Artist ID 	
	$.ajax({
		url: "http://ws.audioscrobbler.com/2.0/?method=artist.getInfo&mbid="+ artistID +"&api_key="+ apikey+"&format=json",
		dataType: "jsonp",
		cache: true,
		success: function(data){
			if ( data.artist !== undefined ) {
				var imageUrl = data.artist.image[size]['#text'];
			}
			if (data.error) {
				getArtistName();
			} else {
				if ( data.artist === undefined || imageUrl == "" || imageUrl == undefined ) {
					var imageLarge = "#";
					var imageUrl = "interfaces/brink/images/no-cover-artist.png";
				} else {
					var artist = data.artist.mbid;
					var artistBio = data.artist.bio.summary;
					var imageLarge = data.artist.image[4]['#text'];
					var imageUrl = data.artist.image[size]['#text'];
				}		
				var artistBio = artistBio;				
				var image = imgElem;
				var bio = $('.artist-bio-container .artist-bio');	
				$(image).attr("src",imageUrl).removeAttr("width").removeAttr("height").hide().fadeIn();
				if ( bio.length > 0 ) $(bio).append(artistBio);
				$(image).wrap('<a href="artistPage?ArtistID='+ artistID +'"></a>');
			}
		}				
	});
	// If not found get by Name
	function getArtistName() {
		$.ajax({
			url: "http://ws.audioscrobbler.com/2.0/?method=artist.getInfo&artist="+ name +"&api_key="+ apikey+"&format=json",
			dataType: "jsonp",
			success: function(data){
				if ( data.artist !== undefined ) {
					var imageUrl = data.artist.image[size]['#text'];
				}
				if ( data.artist === undefined || imageUrl == "" ) {
					var imageLarge = "#";
					var imageUrl = "interfaces/brink/images/no-cover-artist.png";
				} else {
					var artist = data.artist.name;
					var artistBio = data.artist.bio.summary;
					var imageLarge = data.artist.image[4]['#text'];
					var imageUrl = data.artist.image[size]['#text'];
				}		
				var artistBio = artistBio;				
				var image = imgElem;
				var bio = $('.artist-bio-container .artist-bio');	
				$(image).attr("src",imageUrl).removeAttr("width").removeAttr("height").hide().fadeIn();
				if ( bio.length > 0 ) $(bio).append(artistBio);
				$(image).wrap('<a href="artistPage?ArtistID=' + artistID + '" rel="dialog" title="' + artist + '"></a>');
			}				
		});
	}
}

function getAlbumInfo(name, album, elem,size) {
	var apikey = "690e1ed3bc00bc91804cd8f7fe5ed6d4";	
	var dimensions = getOriginalWidthOfImg(this);
	var cover = $(elem);
	
	if ( dimensions <= 1) {
		// Get Data
		$.ajax({
			url: "http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key=" + apikey + "&artist="+ name +"&album="+ album +"&format=json&callback=?",
			dataType: "jsonp",
			success: function(data){
				if ( data.artist !== undefined ) {
					var imageUrl = data.artist.image[size]['#text'];
				}
				if (data.album === undefined || imageUrl == "")  {
					if ( elem.width() == 50 ) {
						var imageUrl = "interfaces/brink/images/no-cover-artist.png";
					} else {
						var imageUrl = "interfaces/brink/images/no-cover-art.png";
					}
				} else {
					var imageUrl = data.album.image[size]['#text'];		
					var imageLarge = data.album.image[3]['#text'];			
				}
				$(cover).error(function(){
					if ( elem.width() == 50 ) {
						var imageUrl = "interfaces/brink/images/no-cover-artist.png";
					} else {
						var imageUrl = "interfaces/brink/images/no-cover-art.png";
					}
					$(elem).css("background", "url("+ imageUrl+") center top no-repeat");
				});
				if ( imageUrl == "") {
					if ( elem.width() == 50 ) {
						var imageUrl = "interfaces/brink/images/no-cover-artist.png";
					} else {
						var imageUrl = "interfaces/brink/images/no-cover-art.png";
					}
					$(elem).css("background", "url("+ imageUrl+")");
				} 
				$(elem).css("background", "url("+ imageUrl+") center top no-repeat");
				$(elem).wrap('<a href="'+ imageLarge +'" rel="dialog" title="' + name + '"></a>');
			}
		});
	}
}

function getOriginalWidthOfImg(img_element) {
    var t = new Image();
    t.src = (img_element.getAttribute ? img_element.getAttribute("src") : false) || img_element.src;
    return t.width;
}

function replaceEmptyAlbum(elem,name,album) {
	var album = $(elem);
	var artist = name;
	var albumname = album;
	var apikey = "690e1ed3bc00bc91804cd8f7fe5ed6d4";
	var dimensions = getOriginalWidthOfImg(this);
	var cover = $(this);
	var url;
	if ( dimensions <= 1) {
		url = "http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key=" + apikey + "&artist="+ artist +"&album="+ albumname +"&format=json&callback=?";
		var imageUrl;
		$.getJSON(url, function(data, response) {
			if (data.album === undefined)  {
				imageUrl = "interfaces/brink/images/no-cover-art.png";
			} else {
				imageUrl = data.album.image[3]['#text'];	
				imageLarge = data.album.image[4]['#text'];					
			// If Last.fm don't provide a cover then use standard
			}
			$(cover).error(function(){
				imageUrl = "interfaces/brink/images/no-cover-art.png";
				$(this).hide().attr("src", imageUrl).show();
			})
			if ( imageUrl == "") {
				imageUrl = "interfaces/brink/images/no-cover-art.png";
				$(this).hide().attr("src", imageUrl).show();
			}
			$(cover).hide().attr("src", imageUrl).show();
			$(cover).wrap('<a href="'+ imageLarge +'" rel="dialog" title="' + artist + " - " + albumname + '"></a>');
		});
	} 	
}

//Mark current active link
$(document).ready(function() {
	enit();
    $("#nav li a").each(function () {
        var hreflink = $(this).attr("href");
		var locationHref = location.href.split("/").pop();
        if (hreflink == locationHref) {
            $(this).parent().addClass("selected");
		}
    });
});

// Loader
var loaderSymbols = ['0', '1', '2', '3', '4', '5', '6', '7'], 
loaderRate = 100, 
loaderIndex = 0, 
loader = function() { 
	$('.loader').text( loaderSymbols[loaderIndex] );
	loaderIndex = loaderIndex  < loaderSymbols.length - 1 ? loaderIndex + 1 : 0; 
	setTimeout(loader, loaderRate); 
}; 
loader(); 

function enit()
{
	var mainWindow = $("#main");
	var totalHeight = $(window).height() - ($("#header").outerHeight() + $("#footer").outerHeight()) - 3;
	$(mainWindow).height(totalHeight);
	$(mainWindow).jScrollPane({ showArrows: true, animateScroll: true, hijackInternalLinks: true, autoReinitialise: true });
}
$(document).ready(function(){
	$("ul#nav-view li").toggle(function() {
		$(this).children("span").removeClass("Icon");
		$(this).children("span").addClass("List");
		$("#gridView").hide();
		$("#listView").show();
		enit();
		}, function() {
		$(this).children("span").removeClass("List");
		$(this).children("span").addClass("Icon");
		$("#gridView").show();
		$("#listView").hide();
	});
});


