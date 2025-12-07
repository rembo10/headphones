"use strict";
// Cache system is a bit outdated and could do with work
Object.defineProperty(exports, "__esModule", { value: true });
exports.default = (function (window, options, logger) {
    var cache = null;
    if (options.env !== 'development') {
        try {
            cache = (typeof window.localStorage === 'undefined') ? null : window.localStorage;
        }
        catch (_) { }
    }
    return {
        setCSS: function (path, lastModified, modifyVars, styles) {
            if (cache) {
                logger.info("saving ".concat(path, " to cache."));
                try {
                    cache.setItem(path, styles);
                    cache.setItem("".concat(path, ":timestamp"), lastModified);
                    if (modifyVars) {
                        cache.setItem("".concat(path, ":vars"), JSON.stringify(modifyVars));
                    }
                }
                catch (e) {
                    // TODO - could do with adding more robust error handling
                    logger.error("failed to save \"".concat(path, "\" to local storage for caching."));
                }
            }
        },
        getCSS: function (path, webInfo, modifyVars) {
            var css = cache && cache.getItem(path);
            var timestamp = cache && cache.getItem("".concat(path, ":timestamp"));
            var vars = cache && cache.getItem("".concat(path, ":vars"));
            modifyVars = modifyVars || {};
            vars = vars || '{}'; // if not set, treat as the JSON representation of an empty object
            if (timestamp && webInfo.lastModified &&
                (new Date(webInfo.lastModified).valueOf() ===
                    new Date(timestamp).valueOf()) &&
                JSON.stringify(modifyVars) === vars) {
                // Use local copy
                return css;
            }
        }
    };
});
//# sourceMappingURL=cache.js.map