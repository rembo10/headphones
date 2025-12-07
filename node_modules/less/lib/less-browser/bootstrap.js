"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var tslib_1 = require("tslib");
/**
 * Kicks off less and compiles any stylesheets
 * used in the browser distributed version of less
 * to kick-start less using the browser api
 */
var default_options_1 = tslib_1.__importDefault(require("../less/default-options"));
var add_default_options_1 = tslib_1.__importDefault(require("./add-default-options"));
var index_1 = tslib_1.__importDefault(require("./index"));
var options = (0, default_options_1.default)();
if (window.less) {
    for (var key in window.less) {
        if (Object.prototype.hasOwnProperty.call(window.less, key)) {
            options[key] = window.less[key];
        }
    }
}
(0, add_default_options_1.default)(window, options);
options.plugins = options.plugins || [];
if (window.LESS_PLUGINS) {
    options.plugins = options.plugins.concat(window.LESS_PLUGINS);
}
var less = (0, index_1.default)(window, options);
exports.default = less;
window.less = less;
var css;
var head;
var style;
// Always restore page visibility
function resolveOrReject(data) {
    if (data.filename) {
        console.warn(data);
    }
    if (!options.async) {
        head.removeChild(style);
    }
}
if (options.onReady) {
    if (/!watch/.test(window.location.hash)) {
        less.watch();
    }
    // Simulate synchronous stylesheet loading by hiding page rendering
    if (!options.async) {
        css = 'body { display: none !important }';
        head = document.head || document.getElementsByTagName('head')[0];
        style = document.createElement('style');
        style.type = 'text/css';
        if (style.styleSheet) {
            style.styleSheet.cssText = css;
        }
        else {
            style.appendChild(document.createTextNode(css));
        }
        head.appendChild(style);
    }
    less.registerStylesheetsImmediately();
    less.pageLoadFinished = less.refresh(less.env === 'development').then(resolveOrReject, resolveOrReject);
}
//# sourceMappingURL=bootstrap.js.map