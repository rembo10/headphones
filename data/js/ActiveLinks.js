//Mark current active link
$(document).ready(function () {
    $("#nav li a").each(function () {
        var hreflink = $(this).attr("href");
        if (hreflink == location.href.split("/").pop()) {
            $(this).parent().addClass("selected");
        }
    });
});
//Resize #main to fit window size
$(document).ready(function () {
	windowWidth = $(window).width();
	windowHeight = $(window).height();
	menuWidth = $("#nav").width();
	$("#main").width(windowWidth - menuWidth - 40);
});

//On window resize
$(window).resize(function () {
	windowWidth = $(window).width();
	windowHeight = $(window).height();
	menuWidth = $("#nav").width();
	$("#main").width(windowWidth - menuWidth - 40);
});