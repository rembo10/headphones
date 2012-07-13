$(document).ready(function() {
	$("img.getImgLink").each(function(){
		var artistId = $(this).attr('for');
		var image = $(this).attr('src');
		alert(artistId);
		
		$.ajax({
			url: "getImageLinks?ArtistID=" + artistId,
			success: function(data){
				var artistImg = data;
				$(image).attr("src",artistImg);
			}
		});
	});
	});
	$("img.getThumb").each(function(){
		var artistId = $(this).attr('for');
		var image = $(this).attr('src');
		alert(artistId);
		
		$.ajax({
			url: "getImageLinks?ArtistID=" + artistId,
			success: function(data){
				var artistImg = data;
				$(image).attr("src",artistImg);
			}
		});
	});
	});
})