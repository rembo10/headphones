/**
 * @file headphones.js
 * @brief Main JavaScript file for Headphones web interface.
 * Contains core UI, API, and utility functions.
 */

var Headphones = Headphones || {};

// --- Configuration ---
Headphones.config = {
    fallbackImage: "interfaces/default/images/no-cover-art.png", // Generic fallback
    fallbackArtistImage: "interfaces/default/images/no-cover-artist.png", // Specific artist fallback
    messageTimeout: 3000 // Default timeout for messages in milliseconds
};

// --- UI Messaging Module ---
Headphones.UI = Headphones.UI || {};
Headphones.UI.Message = (function() {
    var $ajaxMsg = $("#ajaxMsg");
    var $ajaxMsg2 = $("#ajaxMsg2"); // Assuming this is for artist-specific messages
    var $updateBar = $("#updatebar");

    /**
     * Shows a feedback message to the user.
     * @param {string} msg - The message to display.
     * @param {string} type - Type of message ('success', 'error', 'info', 'loading').
     * @param {number} [timeout=Headphones.config.messageTimeout] - Duration to display the message (in ms). Set to 0 for no timeout.
     * @param {HTMLElement} [$targetElement=$ajaxMsg] - The jQuery element to display the message in.
     */
    function showMessage(msg, type, timeout, $targetElement) {
        timeout = typeof timeout !== 'undefined' ? timeout : Headphones.config.messageTimeout;
        $targetElement = $targetElement || $ajaxMsg;

        // Adjust position if update bar is visible
        if ($updateBar.is(":visible")) {
            var height = $updateBar.height() + 35;
            $targetElement.css("bottom", height + "px");
        } else {
            $targetElement.removeAttr("style");
        }

        $targetElement.fadeIn();
        $targetElement.removeClass('success error info'); // Clear previous states

        var iconClass = '';
        switch (type) {
            case 'success':
                iconClass = 'fa-check';
                $targetElement.addClass('success');
                break;
            case 'error':
                iconClass = 'fa-exclamation-triangle';
                $targetElement.addClass('error');
                break;
            case 'loading':
                iconClass = 'fa-refresh fa-spin';
                break;
            default: // info
                iconClass = 'fa-info-circle';
                $targetElement.addClass('info');
        }

        var $message = $("<div class='msg'><i class='fa " + iconClass + "'></i> " + msg + "</div>");
        $targetElement.empty().append($message); // Clear and append new message

        if (timeout > 0) {
            setTimeout(function() {
                $message.fadeOut(function() {
                    $(this).remove();
                    $targetElement.fadeOut();
                });
            }, timeout);
        }
    }

    /**
     * Specific function for artist messages (if still needed, otherwise consolidate into showMessage)
     * @param {string} msg - The message to display.
     */
    function showArtistMessage(msg) {
        showMessage(msg, 'loading', 0, $ajaxMsg2); // No timeout for loading message
    }

    return {
        show: showMessage,
        showArtist: showArtistMessage // Consider removing if not distinct enough
    };
})();

// --- API / AJAX Module ---
Headphones.API = (function() {
    /**
     * Performs an AJAX call with standardized messaging and reload options.
     * @param {object} options - Configuration options for the AJAX call.
     * @param {string} options.url - The URL for the AJAX request.
     * @param {object|string} [options.data] - Data to send with the request.
     * @param {string} [options.type='POST'] - HTTP method ('GET' or 'POST').
     * @param {string} [options.successMessage='Success!'] - Message to display on success.
     * @param {string} [options.errorMessage='There was an error'] - Message to display on error.
     * @param {string} [options.reloadType] - Type of reload after success ('table', 'tabs', 'page', 'submenu', 'submenu&table').
     * @param {HTMLElement} [options.contextElement] - The DOM element that triggered the action (for data-attributes).
     * @param {function} [options.beforeSendCallback] - Custom function to call before sending.
     * @param {function} [options.successCallback] - Custom function to call on success.
     * @param {function} [options.errorCallback] - Custom function to call on error.
     * @param {function} [options.completeCallback] - Custom function to call on completion.
     */
    function doAjaxCall(options) {
        var opts = $.extend(true, {
            url: '',
            data: {},
            type: 'POST',
            successMessage: 'Success!',
            errorMessage: 'There was an error',
            reloadType: null, // 'table', 'tabs', 'page', 'submenu', 'submenu&table'
            contextElement: null,
            beforeSendCallback: null,
            successCallback: null,
            errorCallback: null,
            completeCallback: null
        }, options);

        // Get messages from data attributes if context element provided
        if (opts.contextElement) {
            var $elem = $(opts.contextElement);
            opts.successMessage = $elem.data('success') || opts.successMessage;
            opts.errorMessage = $elem.data('error') || opts.errorMessage;
        }

        $.ajax({
            url: opts.url,
            data: opts.data,
            type: opts.type,
            beforeSend: function(jqXHR, settings) {
                Headphones.UI.Message.show('Loading...', 'loading', 0); // Show loading message indefinitely
                if (opts.beforeSendCallback) opts.beforeSendCallback(jqXHR, settings);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                Headphones.UI.Message.show(opts.errorMessage, 'error');
                if (opts.errorCallback) opts.errorCallback(jqXHR, textStatus, errorThrown);
            },
            success: function(data, textStatus, jqXHR) {
                Headphones.UI.Message.show(opts.successMessage, 'success');
                if (opts.successCallback) opts.successCallback(data, textStatus, jqXHR);

                // Handle reloads based on reloadType
                setTimeout(function() { // Wait for message to fade out
                    if (opts.reloadType === 'table') {
                        Headphones.UI.Content.refreshTable();
                    } else if (opts.reloadType === 'tabs') {
                        Headphones.UI.Content.refreshTab();
                    } else if (opts.reloadType === 'page') {
                        location.reload();
                    } else if (opts.reloadType === 'submenu') {
                        Headphones.UI.Content.refreshSubmenu();
                    } else if (opts.reloadType === 'submenu&table') {
                        Headphones.UI.Content.refreshSubmenu();
                        Headphones.UI.Content.refreshTable();
                    }
                }, Headphones.config.messageTimeout + 100); // Wait for message fade out
            },
            complete: function(jqXHR, textStatus) {
                // The message will fade out automatically by showMessage
                if (opts.completeCallback) opts.completeCallback(jqXHR, textStatus);
            }
        });
    }

    /**
     * Performs a simple GET AJAX call without complex messaging or reload.
     * @param {string} url - The URL for the GET request.
     */
    function doSimpleAjaxCall(url) {
        $.ajax({ url: url, type: 'GET' });
    }

    return {
        call: doAjaxCall,
        simpleCall: doSimpleAjaxCall
    };
})();

// --- Image Loading Module ---
Headphones.Images = (function() {
    /**
     * Loads artwork/thumbnail for an element, handling lazy load and fallbacks.
     * @param {jQuery} $imgElem - The jQuery image element.
     * @param {string} id - The ID (AlbumID or ArtistID).
     * @param {string} type - 'album' or 'artist'.
     * @param {boolean} [unveil=false] - Whether to use data-src and unveil for lazy loading.
     */
    function loadImage($imgElem, id, type, unveil) {
        var infoURL = "getImageLinks?" + (type === 'artist' ? "ArtistID=" : "AlbumID=") + id;

        $.ajax({
            url: infoURL,
            cache: true,
            dataType: "json",
            success: function(data) {
                var imageUrl = Headphones.config.fallbackImage;
                var artworkUrl = Headphones.config.fallbackImage;

                if (data) {
                    imageUrl = data.thumbnail || (type === 'artist' ? Headphones.config.fallbackArtistImage : Headphones.config.fallbackImage);
                    artworkUrl = data.artwork || (type === 'artist' ? Headphones.config.fallbackArtistImage : Headphones.config.fallbackImage);
                }

                if (unveil) {
                    $imgElem.attr("data-src", imageUrl);
                    $imgElem.unveil(); // Trigger unveil for lazy loading
                } else {
                    $imgElem.attr("src", imageUrl).hide().fadeIn(); // Direct load with fade
                }

                // If element has a rel="dialog" parent, update href for Fancybox
                var $wrapper = $imgElem.closest('a[rel="dialog"]');
                if ($wrapper.length) {
                    $wrapper.attr('href', artworkUrl); // Link to full artwork
                }
            },
            error: function() {
                // On error, set to fallback image if not already set or handled by onerror on HTML
                if (unveil) {
                    $imgElem.attr("data-src", Headphones.config.fallbackImage);
                    $imgElem.unveil();
                } else {
                    $imgElem.attr("src", Headphones.config.fallbackImage).hide().fadeIn();
                }
            }
        });
    }

    /**
     * Fetches and appends summary information.
     * @param {jQuery} $elem - The element to append summary to.
     * @param {string} id - The ID (AlbumID or ArtistID).
     * @param {string} type - 'album' or 'artist'.
     */
    function getInfo($elem, id, type) {
        var infoURL = "getInfo?" + (type === 'artist' ? "ArtistID=" : "AlbumID=") + id;
        $.ajax({
            url: infoURL,
            cache: true,
            dataType: "json",
            success: function(data) {
                if (data && data.Summary) {
                    $elem.append(data.Summary);
                }
            }
        });
    }

    return {
        load: loadImage,
        getInfo: getInfo
    };
})();

// --- UI Content Refresh Module ---
Headphones.UI.Content = (function() {
    /**
     * Refreshes a specific part of the page content.
     * @param {string} targetSelector - jQuery selector for the element to load content into.
     * @param {string} sourceContentSelector - jQuery selector for the content to extract from the source URL.
     * @param {function} [initCallback] - Callback function to run after content is loaded.
     */
    function refreshPart(targetSelector, sourceContentSelector, initCallback) {
        var url = window.location.href;
        $(targetSelector).load(url + " " + sourceContentSelector, function(response, status, xhr) {
            if (status === "error") {
                console.error("Failed to load content for " + targetSelector + ": " + xhr.status + " " + xhr.statusText);
                Headphones.UI.Message.show("Failed to refresh content.", 'error');
            } else if (initCallback) {
                // Ensure the callback is part of the Headphones object if it relies on it
                if (typeof initCallback === 'string' && Headphones.hasOwnProperty(initCallback)) {
                    Headphones[initCallback](); // Call the global Headphones function
                } else if (typeof initCallback === 'function') {
                    initCallback();
                }
            }
        });
    }

    /** Refreshes the submenu by reloading its content. */
    function refreshSubmenu() {
        refreshPart("#subhead_container", "#subhead_menu", Headphones.UI.initActions); // Pass initActions to re-apply handlers
    }

    /** Refreshes the main table content. */
    function refreshTable() {
        // This assumes there's one main .display table. If multiple, refine selector.
        // The original also reloaded tbody and thead separately, which is fine.
        refreshPart("table.display", "table.display tbody, table.display thead", function() {
            // Re-initialize DataTables after table refresh.
            // This might need specific DataTable re-initialization logic for each page.
            // A more robust solution would be to destroy and recreate the DataTable.
            // The template-specific `initThisPage()` usually contains this.
            // We need to call the appropriate initThisPage for the current page.
            // As `initThisPage` is defined per HTML file, we rely on the specific page's ready handler
            // to call its own initThisPage, or pass it as a parameter if this is called generically.
            // For now, let's assume `initThisPage` exists in the global scope where refreshTable is called.
            if (typeof initThisPage === 'function') {
                initThisPage();
            } else if (typeof SearchResultsPage !== 'undefined' && typeof SearchResultsPage.initDataTable === 'function') {
                SearchResultsPage.initDataTable();
            }
            // ... add more page-specific re-initializations as needed
        });
    }

    /** Refreshes the currently active tab content. */
    function refreshTab() {
        var tabId = $('.ui-tabs-panel:visible').attr("id");
        if (tabId) {
            refreshPart('.ui-tabs-panel:visible', "#" + tabId, function() {
                // Similar to refreshTable, re-initialize specific tab content
                if (typeof initThisPage === 'function') { // assuming initThisPage handles tab content
                    initThisPage();
                }
            });
        }
    }

    /**
     * Polls for status changes on rows with 'gradeL' class (loading state).
     * This is an older polling pattern; consider WebSockets for real-time updates if performance is critical.
     */
    function refreshLoadArtist() {
        var $loadingRows = $("table.display tr.gradeL");
        if ($loadingRows.length > 0) {
            $loadingRows.each(function() {
                var $row = $(this);
                // Reload only the row's content to check status
                var rowIndex = $row.index() + 1; // 1-based index
                var url = window.location.href;
                $row.load(url + " table.display tbody tr:nth-child(" + rowIndex + ") td", function(response, status, xhr) {
                    if (status === "error") {
                        console.error("Failed to load row status: " + xhr.status + " " + xhr.statusText);
                        // Optional: Show a message to the user
                    } else {
                        // Check status after loading the updated row content
                        if ($row.find(".column-status").text() === 'Active') { // Assuming a status column with this text
                            $row.removeClass('gradeL').addClass('gradeZ');
                            // Re-initialize relevant JS if needed for the row (e.g., DataTables redrawing)
                            if (typeof initThisPage === 'function') initThisPage(); // Re-initialize the table/page
                        } else {
                            // If still loading, set timeout for next check
                            setTimeout(refreshLoadArtist, 3000);
                        }
                    }
                });
            });
        }
    }


    return {
        refreshSubmenu: refreshSubmenu,
        refreshTable: refreshTable,
        refreshTab: refreshTab,
        refreshLoadArtist: refreshLoadArtist
    };
})();

// --- UI Element Initialization Module ---
Headphones.UI.Elements = (function() {
    /** Initializes the header scroll-fade effect. */
    function initHeader() {
        var $header = $("#container header");
        var fadeSpeed = 100,
            fadeTo = 0.5,
            topDistance = 20;
        var inside = false;

        $(window).on('scroll', function() {
            var position = $(window).scrollTop();
            if (position > topDistance && !inside) {
                //add events
                $header.fadeTo(fadeSpeed, fadeTo);
                $header.on('mouseenter', function() {
                    $header.fadeTo(fadeSpeed, 1);
                });
                $header.on('mouseleave', function() {
                    $header.fadeTo(fadeSpeed, fadeTo);
                });
                $("#toTop").fadeIn();
                inside = true;
            } else if (position < topDistance && inside) { // Added '&& inside' to prevent re-triggering
                $header.fadeTo(fadeSpeed, 1); // Ensure it's fully visible at top
                $header.off('mouseenter mouseleave'); // Remove events when at top
                $("#toTop").fadeOut();
                inside = false;
            }
        });
    }

    /**
     * Initializes config checkboxes to show/hide sibling content.
     * @param {HTMLElement} elem - The checkbox DOM element.
     */
    function initConfigCheckbox(elem) {
        var $checkbox = $(elem);
        var $configContent = $checkbox.parent().next();

        // Initial state
        if ($checkbox.is(":checked")) {
            $configContent.show();
        } else {
            $configContent.hide();
        }

        // Click handler
        $checkbox.on('click', function() {
            if ($(this).is(":checked")) {
                $configContent.slideDown();
            } else {
                $configContent.slideUp();
            }
        });
    }

    /** Initializes various action buttons with jQuery UI button styling. */
    function initActions() {
        // Select all menu links under #subhead_menu and apply button()
        // This assumes jQuery UI Button widget is available and desired.
        $("#subhead_menu a[id^='menu_link_'], #subhead_menu .menu_link_edit").button();
    }

    return {
        initHeader: initHeader,
        initConfigCheckbox: initConfigCheckbox,
        initActions: initActions
    };
})();

// --- Utility Functions Module ---
Headphones.Utils = (function() {
    /**
     * Sets placeholder text for DataTables search input.
     * @param {string} text - The placeholder text.
     */
    function resetFilters(text) {
        // Ensure this targets the correct search input for DataTables
        if ($(".dataTables_filter input").length > 0) {
            $(".dataTables_filter input").attr("placeholder", "filter " + text + "");
        }
    }

    /** Initializes Fancybox for dialog links. */
    function initFancybox() {
        // Check if Fancybox script is already loaded or needs to be loaded dynamically
        if ($.fn.fancybox) { // Check if fancybox function exists on jQuery object
            $("a[rel=dialog]").fancybox();
        } else if ($("a[rel=dialog]").length > 0) {
            // Dynamically load Fancybox script and CSS if elements with rel=dialog exist
            $.getScript('interfaces/default/js/fancybox/jquery.fancybox-1.3.4.js', function() {
                $("head").append("<link rel='stylesheet' href='interfaces/default/js/fancybox/jquery.fancybox-1.3.4.css'>");
                $("a[rel=dialog]").fancybox();
            }).fail(function(jqxhr, settings, exception) {
                console.error("Failed to load Fancybox script: ", exception);
            });
        }
    }

    return {
        resetFilters: resetFilters,
        initFancybox: initFancybox
    };
})();


// --- Global Functions (for backward compatibility if needed, but prefer to call from Headphones object) ---
// These global functions would ideally be removed and replaced with direct calls to Headphones.API, Headphones.UI, etc.
// For a gradual transition, they can act as wrappers.

// Original getThumb / getImageLinks replacement
function getImageLinks(elem, id, type, unveil) {
    Headphones.Images.load($(elem), id, type, unveil);
}

// Original getInfo replacement
function getInfo(elem, id, type) {
    Headphones.Images.getInfo($(elem), id, type);
}

// Original doAjaxCall replacement (needs careful integration with new params)
// The HTML templates are passing doAjaxCall(url,elem,reload,form).
// This wrapper needs to convert those to the new options object.
function doAjaxCall(url, elem, reloadType, isFormSubmission) {
    var options = {
        url: url,
        contextElement: elem,
        reloadType: reloadType
    };

    if (isFormSubmission) {
        // This part needs careful migration. The original `doAjaxCall`
        // had logic like `var formID = "#"+url; var dataString = $(formID).serialize();`
        // and validation like `if ( $('td#select input[type=checkbox]').length > 0 && !$('td#select input[type=checkbox]').is(':checked') ... )`.
        // This validation MUST be done *before* calling doAjaxCall in the specific HTML template's JS.
        // Here, we assume `url` is the form ID if `isFormSubmission` is true.
        var $form = $('#' + url); // Assuming url is the form ID
        if ($form.length) {
            options.data = $form.serialize();
        } else {
             console.warn("doAjaxCall: form with ID '" + url + "' not found for submission.");
             // If the form cannot be found, it should likely be an error.
             Headphones.UI.Message.show("Form not found for submission.", 'error');
             return false;
        }
    }
    Headphones.API.call(options);
}

function doSimpleAjaxCall(url) {
    Headphones.API.simpleCall(url);
}

function resetFilters(text) {
    Headphones.Utils.resetFilters(text);
}

function initFancybox() {
    Headphones.Utils.initFancybox();
}

// Placeholder for `initThisPage` - this function is typically defined per HTML template.
// It's called by `$(document).ready` in many templates.
// This should be removed from `headphones.js` and defined in each template.
// function initThisPage() { /* defined in each HTML template */ }


// --- Document Ready ---
$(document).ready(function() {
    Headphones.UI.Elements.initHeader(); // Initialize global header effects
    Headphones.UI.Elements.initActions(); // Initialize global action buttons (jQuery UI)

    // Ensure `initThisPage()` is called from the individual HTML template's ready handler.
    // This `script.js` file should be included *before* the template's specific script block.
});
