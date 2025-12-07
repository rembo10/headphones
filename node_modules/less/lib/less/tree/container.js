"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var tslib_1 = require("tslib");
var ruleset_1 = tslib_1.__importDefault(require("./ruleset"));
var value_1 = tslib_1.__importDefault(require("./value"));
var selector_1 = tslib_1.__importDefault(require("./selector"));
var atrule_1 = tslib_1.__importDefault(require("./atrule"));
var nested_at_rule_1 = tslib_1.__importDefault(require("./nested-at-rule"));
var Container = function (value, features, index, currentFileInfo, visibilityInfo) {
    this._index = index;
    this._fileInfo = currentFileInfo;
    var selectors = (new selector_1.default([], null, null, this._index, this._fileInfo)).createEmptySelectors();
    this.features = new value_1.default(features);
    this.rules = [new ruleset_1.default(selectors, value)];
    this.rules[0].allowImports = true;
    this.copyVisibilityInfo(visibilityInfo);
    this.allowRoot = true;
    this.setParent(selectors, this);
    this.setParent(this.features, this);
    this.setParent(this.rules, this);
};
Container.prototype = Object.assign(new atrule_1.default(), tslib_1.__assign(tslib_1.__assign({ type: 'Container' }, nested_at_rule_1.default), { genCSS: function (context, output) {
        output.add('@container ', this._fileInfo, this._index);
        this.features.genCSS(context, output);
        this.outputRuleset(context, output, this.rules);
    }, eval: function (context) {
        if (!context.mediaBlocks) {
            context.mediaBlocks = [];
            context.mediaPath = [];
        }
        var media = new Container(null, [], this._index, this._fileInfo, this.visibilityInfo());
        if (this.debugInfo) {
            this.rules[0].debugInfo = this.debugInfo;
            media.debugInfo = this.debugInfo;
        }
        media.features = this.features.eval(context);
        context.mediaPath.push(media);
        context.mediaBlocks.push(media);
        this.rules[0].functionRegistry = context.frames[0].functionRegistry.inherit();
        context.frames.unshift(this.rules[0]);
        media.rules = [this.rules[0].eval(context)];
        context.frames.shift();
        context.mediaPath.pop();
        return context.mediaPath.length === 0 ? media.evalTop(context) :
            media.evalNested(context);
    } }));
exports.default = Container;
//# sourceMappingURL=container.js.map