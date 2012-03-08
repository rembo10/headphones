$(document).ready(function () {
    $("#nav li a").each(function () {
        var hreflink = $(this).attr("href");
        if (hreflink == location.href.split("/").pop()) {
            $(this).parent().addClass("selected");
        }
    });
});