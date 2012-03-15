/*/////////////////////////////////////////////////////////////////////////////////
VERSION 1.3 - Updated January 4, 2011
CREATED BY KEVIN MACK
DETAILS: http://nicetransition.com/_plugins/jQuery-Cross-Browser-Select-Fix 
//////////////////////////////////////////////////////////////////////////////////*/
(function ($) {
    $.fn.selectFix = function (options) {
        $(this).each(function () {

            var settings = $.extend({ 'extraStyles': true, 'responsive': false, 'arrow': true, 'arrowWidth': 20, 'arrowContent': '', 'className': 'select', 'classText': 'text', 'classArrow': 'arrow', 'classFocus': 'focused', 'classEnd': 'selected', 'display': 'inline-block' }, options);

            var className = "." + settings.className;
            var selectField = $(this);

            selectField.css({ '-webkit-appearance': 'none', 'box-sizing': 'border-box', '-moz-box-sizing': 'border-box', '-webkit-box-sizing': 'border-box', 'cursor': 'pointer' }); //mac OS bug fix on webkit render

            var initVal;
            if (selectField.children("option:selected").size() > 0) {
                initVal = selectField.children("option:selected").eq(0).text();
            } else {
                initVal = selectField.children("option").eq(0).text();
            }

            var height = selectField.css("height");
            var width = selectField.css("width").replace("px", "");
            var widthPercent;

            if (settings.responsive) {
                widthPercent = (100 * parseInt(width.replace("px", "")) / parseInt(selectField.parent().css('width').replace("px", ""))) + '%';
            } else {
                widthPercent = width + "px";
            }

            var arrow;
            var arrowWidth = String(settings.arrowWidth);

            if (arrowWidth.indexOf('px') < 0 && arrowWidth.indexOf('%') < 0) {
                arrowWidth = arrowWidth + "px";
            }
            if (settings.arrow == true) {
                arrow = "<span style=\"display: block; height: 100%; position: absolute; right: 0; width: " + arrowWidth + ";\" class=\"" + settings.classArrow + "\">" + settings.arrowContent + "</span>";
            } else {
                arrow = "";
            }

            selectField.css({ "display": "block", "left": 0, "opacity": 0, "position": "absolute", "top": 0, "z-index": 1 }).wrap("<div class=\"" + settings.className + "\"style=\"overflow: hidden; display: " + settings.display + "; position: relative;  width: " + widthPercent + ";\"></div>").closest(className).append("<span style=\"display: block; left: 0; height: " + height + "; line-height: inherit; position: absolute; top: 0; width: 100%;\" class=\"" + settings.classText + "\">" + initVal + "</span>" + arrow);

            selectField.bind({
                change: function (event) {
                    selectField.siblings("." + settings.classText).html(selectField.children("option[value=" + selectField.val() + "]").text());
                    if (settings.extraStyles == true) {
                        selectField.parent(className).addClass(settings.classEnd).removeClass(settings.classFocus); //optional styling to be used once a selection has been made
                    }
                    if (selectField.val() == '' || selectField.val() == undefined || selectField.val() == null) {
                        selectField.parent(className).removeClass(settings.classEnd);
                    }
                },
                focus: function (event) {
                    if (settings.extraStyles == true) {
                        selectField.parent(className).addClass(settings.classFocus);
                    }
                    selectField.keyup(function () {
                        selectField.siblings("." + settings.classText).html($(this).children("option:selected").text());                        
                    });
                },
                click: function () {
                    if (settings.extraStyles == true) {
                        selectField.parent(className).addClass(settings.classFocus);
                    }
                },
                blur: function () {
                    if (settings.extraStyles == true) {
                        selectField.parent(className).removeClass(settings.classFocus);
                    }
                }
            });

            if ($(".stlyesFor" + settings.className).size() < 1) {
                selectField.after("<style type=\"text/css\" class=\"stlyesFor" + settings.className + "\">." + settings.className + " select {width: 100%;}</style>");
            }

        });
    }
})(jQuery)