var triggers;

var numberOfTabs;
var defaultTabNavOpacity = 0.2;
var innerFloatingNavTextSet = false;
var nextElementPlaceHolder;
var prevElementPlaceHolder;
var nextElement;
var prevElement;


// generated in python, used to load saved newsnab sites
var existingNewznabName = [];
var existingNewznabUrl = [];
var existingNewznabApiKey = [];
var existingNewznabId = [];

// perform JavaScript after the document is scriptable.
    $(document).ready(function() {
    // setup ul.tabs to work as tabs for each div directly under div.panes
    $("ul#subhead_menu").tabs("div.panes > div");
    
    // setup tooltips on inputs
    $("div.panes :input").tooltip({

        // place tooltip on the right edge
        position: "center right",

        // a little tweaking of the position
        offset: [-2, 10],

        // use the built-in fadeIn/fadeOut effect
        effect: "fade",

        // custom opacity setting
        opacity: 0.8

    });
    
    // setup form validator for newznab popup
    $("#add_newznab_form").validator({ 
        position: 'top left', 
        offset: [-12, 0],
        message: '<div><em /></div>' // em element is the arrow
    });
    
    // config popup form for newznab
    triggers = $("#add_newznab_button").overlay({mask: '#000', effect: 'apple'});
    
                    
    // setup existing newznab sites 
    var newznabNumber = existingNewznabName.length;
    for(var i = 0; i < newznabNumber; i++) {
        addNewNewzNabSite(existingNewznabName[i], existingNewznabUrl[i], existingNewznabApiKey[i], existingNewznabId[i]);
    }
    
    // assign handlers to form items
    $("#nzb_handler").change(function() {changeNzbHandler();});
    $("input#nzbmatrix").change(function() {toggleDetailsSection("nzbmatrix");});
    $("input#nzbsorg").change(function() {toggleDetailsSection("nzbsorg");});
    $("input#newzbin").change(function() {toggleDetailsSection("newzbin");});
    $("input#newznab").change(function() {toggleDetailsSection("newznab");});
    $("input#detect_bitrate").change(function() {toggleDetailsSection("detect_bitrate", true);});        
    $("input#use_advanced_encoding").change(function() {
        toggleDetailsSection("use_advanced_encoding", false, "advanced_encode_options_details");
        toggleDetailsSection("use_advanced_encoding", true, "standard_audio_details");
    });
    $("input#encode").change(function() {toggleDetailsSection("encode");});
    $("input#folder_format").keyup(function() {generateFolderFormatExample();});
    $("input#file_format").keyup(function() {generateFileFormatExample();});         
    $("input#submit").click(function() {submitForm();});              
    $("input[name='preferred_quality']").change(function() {toggleDetailsSection("preferred_bitrate");});
    
    $("select#encoder").change(function() {changeEncoderSettings();});
    
    $("select#encodervbrcbr").change(function() {changeEncoderVbrCbrSettings();});

    // set initial state of form items
    changeNzbHandler();
    generateFolderFormatExample();
    generateFileFormatExample();
    
    $("#standard_audio_details").toggle(!$("input#use_advanced_encoding")[0].checked);
    $("#advanced_encode_options_details").toggle($("input#use_advanced_encoding")[0].checked);             
    $("#nzbmatrix_details").toggle($("input#nzbmatrix")[0].checked);
    $("#nzbsorg_details").toggle($("input#nzbsorg")[0].checked);
    $("#newzbin_details").toggle($("input#newzbin")[0].checked);
    $("#encode_details").toggle($("input#encode")[0].checked);
    $("#detect_bitrate_details").toggle(!$("input#detect_bitrate")[0].checked);

    $("#preferred_bitrate_details").toggle($("#preferred_bitrate")[0].checked);
    $("dl:has(input[type='checkbox']), dl:has(input[type='radio']), dl:has(select)").each(function() {
        this.className += " flow";
    });
    changeEncoderSettings();
    changeEncoderVbrCbrSettings();
    
    
    // setup next & prev buttons
    numberOfTabs = $("ul#subhead_menu").data("tabs").getTabs().length
   
   nextElement = $("#floating_next");
   prevElement = $("#floating_prev");
   nextElementPlaceHolder = $("#floating_next span")[0];
   prevElementPlaceHolder = $("#floating_prev span")[0];
   
   $(".panes").mousemove(function(event) {
       var PREV = 0;
       var NEXT = 1;
        var args = arguments[0];
        var mousePositionWidthPercent = ((args.clientX - args.currentTarget.offsetLeft) / args.currentTarget.clientWidth);
        var targetElement;
        var navTarget;
        if(mousePositionWidthPercent < 0.5) {
            opacity = 1-(1 * (mousePositionWidthPercent*2));
            targetElement = $(".navigation.previous")[0];
            navtarget = PREV;
        } else {
            opacity = (1 * ((mousePositionWidthPercent-0.5)*2));  
            targetElement = $(".navigation.next")[0];
            navtarget = NEXT;
        }
        opacity = (opacity < defaultTabNavOpacity) ? defaultTabNavOpacity : opacity;
        targetElement.style.opacity = opacity;
        
        if(args.target.className.indexOf("navigation") > -1) {
            var thisIndex = $("ul#subhead_menu").data("tabs").getIndex();
            var floatingElement;
            var targetIndex;
            if(navtarget == PREV) {
                floatingElement = prevElement[0];
            } else {
                floatingElement = nextElement[0]; 
            }
            
            floatingElement.style.display = "block";
            floatingElement.style.top = event.pageY + "px";
            floatingElement.style.left = event.pageX + "px";           
        } else {
            prevElement[0].style.display = "none"; 
            nextElement[0].style.display = "none";
        }
        
        event.preventDefault();
        event.stopPropagation();
   });
    $(".navigation").bind("mouseout", function(event) {
        this.style.opacity=defaultTabNavOpacity;
        event.preventDefault();
        event.stopPropagation();
    });
    
    $(".previous").click(function() {
        var currentIndex = $("ul#subhead_menu").data("tabs").getIndex();
        if(currentIndex > 0) {

            $("ul#subhead_menu").data("tabs").prev();
            innerFloatingNavTextSet = false;
            changeFloatingNavText();
        }
    });
    
    $(".next").click(function() {
        var currentIndex = $("ul#subhead_menu").data("tabs").getIndex();
        if(currentIndex < numberOfTabs) {

            $("ul#subhead_menu").data("tabs").next();
            innerFloatingNavTextSet = false;
            changeFloatingNavText();
        }
    });
    $("ul#subhead_menu").data("tabs").onClick(function(event, clickedTabNumber) {

        manageTabNavButtons(clickedTabNumber);
        innerFloatingNavTextSet = false;
        changeFloatingNavText();
    });
    
    // setup tab navigation buttons on page load
    changeFloatingNavText();
    manageTabNavButtons( $("ul#subhead_menu").data("tabs").getIndex());
    
}, false);

    function changeFloatingNavText() {
        if(!innerFloatingNavTextSet) {
            var thisIndex = $("ul#subhead_menu").data("tabs").getIndex();
            innerFloatingNavTextSet = true;  
            if(thisIndex > 0) {
                prevElementPlaceHolder.innerHTML = $("ul#subhead_menu").data("tabs").getTabs()[thisIndex - 1].innerHTML;
            }
            if(thisIndex+1 < numberOfTabs) {
                nextElementPlaceHolder.innerHTML = $("ul#subhead_menu").data("tabs").getTabs()[thisIndex + 1].innerHTML;
            }
        }
    }
    
function manageTabNavButtons(clickedTabNumber) {
    if(clickedTabNumber == 0) {
        $(".navigation.previous").fadeOut();
        $(".navigation.next").fadeIn();
        prevElement.fadeOut();
    } else if (clickedTabNumber == numberOfTabs-1) {
        $(".navigation.next").fadeOut();
        $(".navigation.previous").fadeIn();
        nextElement.fadeOut();
    } else {
        $(".navigation.next").fadeIn();
        $(".navigation.previous").fadeIn();
    }
} 
    
function changeEncoderSettings() {
    var selectedEncoderType = $("select#encoder option:selected").text().trim();
    if(selectedEncoderType == "lame") {
        $("#encoderoutputformat_mp3")[0].selected = "selected";
        $("#encoderoutputformat_ogg")[0].style.display = "none";
        $("#encoderoutputformat_m4a")[0].style.display = "none";
    } else {
        $("#encoderoutputformat_ogg")[0].style.display = "";
        $("#encoderoutputformat_m4a")[0].style.display = "";           
    }
}
function changeEncoderVbrCbrSettings() {     
    var selectedEncoderVbrCbrType = $("select#encodervbrcbr option:selected").text().trim();
    if(selectedEncoderVbrCbrType == "vbr") {
        $("#bitrate_container").slideUp();
        $("#samplingfrequency_container").slideUp();
        $("#encoderquality_container").slideDown(); 
    } else {
        $("#bitrate_container").slideDown();
        $("#samplingfrequency_container").slideDown();
        $("#encoderquality_container").slideUp();
    }
}

$("#add_newznab form").submit(function(e) {
    
    // close the overlay
    triggers.eq(0).overlay().close();

    // get user input
    var name = $("#add_newznab_name", this).val();
    var url = $("#add_newznab_url", this).val();
    var apikey = $("#add_newznab_apikey", this).val();
    addNewNewzNabSite(name, url, apikey);
    
    // do not submit the form
    return e.preventDefault();
});

function addNewNewzNabSite(name, url, apikey) {
    var newznab_template = $("#newznab_template").html();

    newznab_template = newznab_template.replace(/NAME/g, name)
                        .replace(/URL/g, url)
                        .replace(/APIKEY/g, apikey);
    $("#newznab_site_container").append($(newznab_template));        
}

function submitForm() {
    var currentTab = $("ul#subhead_menu").data("tabs").getCurrentTab();
    $("input#selected_tab").val(currentTab[0].hash);
    return true;
}

function generateFolderFormatExample() {
    var formattedString = $("input#folder_format").val();
    formattedString = formattedString.replace(/lowerfirst/g, "p")
                                        .replace(/first/g, "P")
                                        .replace(/artist/g, "Propagandhi")
                                        .replace(/album/g, "Today's Empires, Tomorrow's Ashes")
                                        .replace(/year/g, "2001");
    $("#folder_format_example").text(formattedString);
}        
function generateFileFormatExample() {        
    var formattedString = $("input#file_format").val();
    formattedString = formattedString.replace(/tracknumber/g, "4")
                                        .replace(/title/g, "Back to the Motor League")
                                        .replace(/artist/g, "Propagandhi")
                                        .replace(/album/g, "Today's Empires, Tomorrow's Ashes")
                                        .replace(/year/g, "2001");
    $("#file_format_example").text(formattedString + ".mp3");
}


function toggleDetailsSection(checkboxName, inverse, detailName) {
    inverse = arguments.length > 1 ? inverse : false;
    detailName = arguments.length > 2 ? detailName : checkboxName + "_details";
    
    var checked = $("input#" + checkboxName)[0].checked;
    checked = inverse ? !checked : checked;

    if(checked) {
        $("#" + detailName).slideDown();
    } else {
        $("#" + detailName).slideUp();
    }
}

function changeNzbHandler() {
    var handlerSections = $("#handler_sections > fieldset");
    handlerSections.each(function() {
        this.style.display = "none";
    })
    handlerSections[$("#nzb_handler")[0].selectedIndex].style.display = "block";
}