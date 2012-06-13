//Mark current active link
$(document).ready(function() {
    $("#nav li a").each(function () {
        var hreflink = $(this).attr("href");
		var locationHref = location.href.split("/").pop();
        if (hreflink == locationHref) {
            $(this).parent().addClass("selected");
		}
    });
});

//Resize #main to fit window size
function mainResize()
{
	var totalHeight = $(window).height() -
					($("#header").outerHeight() + 2 +
					$("#footer").outerHeight());
	$("#main").height(totalHeight);
}

function mainScroll()
{
	$('#main').jScrollPane({
		showArrows: true
	});
}

// Mark Config navi item
$(document).ready(function(){
	$("#nav-config li").click(function(){
		$("#nav-config li.selected").removeClass("selected");
		$(this).addClass("selected");
	});
});

//Smooth scroll bookmarks
$(document).ready(function () {
    $("#nav-config li a").bind("click", function (event) {
        event.preventDefault();
        var target = $(this).attr("href");
        $("#main").stop().animate({
            scrollLeft: $(target).offset().left,
            scrollTop: $(target).offset().top - 100
        }, 1200);
    });
});

//Message dialog close & output
$(document).ready(function(){
	$("#message div .btnClose").click(function(){
		$(this).parent().fadeOut(1000);
	});
});

function messageDialog(type, text){
	document.write(
	  '<div class="dialog ' + type + '">' 
		+ '<div class="btnClose" title="Close" ></div>' //Close
		+ '<div class="image" title="' + type + '"></div>' //Image
		+ '<span>' + text + '</span>' //Message
	+ '</div>');
}

//Add styled class to dataTables_lenght
$(document).ready(function() {
	$(".dataTables_length label select").addClass("styled");
});

//Main fadeIn
$(document).ready(function () {
	$("#main").hide();
	$("#main").fadeIn("slow");
});

//CD Rotate
$(function() {
var $rotateElement = $(".album-art-cd");
rotate(0);
function rotate(degree) {

      // For webkit browsers: e.g. Chrome
    $rotateElement.css({ WebkitTransform: 'rotate(' + degree + 'deg)'});
      // For Mozilla browser: e.g. Firefox
    $rotateElement.css({ '-moz-transform': 'rotate(' + degree + 'deg)'});

      // Animate rotation with a recursive call
    setTimeout(function() { rotate(++degree); },30);
    }
});

