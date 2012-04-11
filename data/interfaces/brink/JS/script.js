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
	//On load set #main height & width
	var totalWidth = $(window).width() -
					($("#nav").outerWidth());
	
	var totalHeight = $(window).height() -
					($("header").outerHeight() + 
					$("#footer").outerHeight());
	
	$("#main").height(totalHeight);
	$("#main").width(totalWidth);
}

//Update close
var closed = true;
$("#updatebar").hide();
$(document).ready(function () {
	$(".btnClose").click(function() {
		$("#updatebar").fadeOut("slow");
		closed = true;
	});
	if(closed == true){
		$("#updatebar").hide();
	}
	if(closed == false){
		$("#updatebar").fadeIn("slow");
	}
});

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

//Acesskey
function accesskey()
{
	document.getElementByClassName('.dataTables_filter div input').accessKey="q";
}

//Config open/close
$(function() {
    $('.configHeadline').click(function() {
        $(this).next('div').slideToggle("slow");
    });
});
