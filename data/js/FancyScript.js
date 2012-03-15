//Mark current active link
$(document).ready(function () {
    $("#nav li a").each(function () {
        var hreflink = $(this).attr("href");
		var locationHref = location.href.split("/").pop();
        if (hreflink == locationHref) {
            $(this).parent().addClass("selected");
		}
    });
});
//Resize #main to fit window size
$(document).ready(function() {
	//On load set #main height & width
	windowWidth = $(window).width();
	windowHeight = $(window).height();
	menuWidth = $("#nav").width();
	headerHeight = $("header").height();
	$("#main").height(windowHeight - headerHeight - 40);
	$("#main").width(windowWidth - menuWidth - 10);
});

//On window resize
$(window).resize(function() {
	windowWidth = $(window).width();
	windowHeight = $(window).height();
	menuWidth = $("#nav").width();
	headerHeight = $("header").height();
	$("#main").height(windowHeight - headerHeight - 40);
	$("#main").width(windowWidth - menuWidth - 10);
});

//Update close
$(document).ready(function () {
	$("#updatebar").hide();
	$("#updatebar").fadeIn("Fast");
	
	$(".btnClose").click(function() {
		$("#updatebar").fadeOut("slow");
	});
});

//Main fadeIn
$(document).ready(function () {
	$("#main").hide();
	$("#main").fadeIn("slow");
});
