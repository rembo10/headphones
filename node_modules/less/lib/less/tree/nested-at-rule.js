"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var tslib_1 = require("tslib");
var ruleset_1 = tslib_1.__importDefault(require("./ruleset"));
var value_1 = tslib_1.__importDefault(require("./value"));
var selector_1 = tslib_1.__importDefault(require("./selector"));
var anonymous_1 = tslib_1.__importDefault(require("./anonymous"));
var expression_1 = tslib_1.__importDefault(require("./expression"));
var utils = tslib_1.__importStar(require("../utils"));
var NestableAtRulePrototype = {
    isRulesetLike: function () {
        return true;
    },
    accept: function (visitor) {
        if (this.features) {
            this.features = visitor.visit(this.features);
        }
        if (this.rules) {
            this.rules = visitor.visitArray(this.rules);
        }
    },
    evalFunction: function () {
        if (!this.features || !Array.isArray(this.features.value) || this.features.value.length < 1) {
            return;
        }
        var exprValues = this.features.value;
        var expr, paren;
        for (var index = 0; index < exprValues.length; ++index) {
            expr = exprValues[index];
            if (expr.type === 'Keyword' && index + 1 < exprValues.length && (expr.noSpacing || expr.noSpacing == null)) {
                paren = exprValues[index + 1];
                if (paren.type === 'Paren' && paren.noSpacing) {
                    exprValues[index] = new expression_1.default([expr, paren]);
                    exprValues.splice(index + 1, 1);
                    exprValues[index].noSpacing = true;
                }
            }
        }
    },
    evalTop: function (context) {
        this.evalFunction();
        var result = this;
        // Render all dependent Media blocks.
        if (context.mediaBlocks.length > 1) {
            var selectors = (new selector_1.default([], null, null, this.getIndex(), this.fileInfo())).createEmptySelectors();
            result = new ruleset_1.default(selectors, context.mediaBlocks);
            result.multiMedia = true;
            result.copyVisibilityInfo(this.visibilityInfo());
            this.setParent(result, this);
        }
        delete context.mediaBlocks;
        delete context.mediaPath;
        return result;
    },
    evalNested: function (context) {
        this.evalFunction();
        var i;
        var value;
        var path = context.mediaPath.concat([this]);
        // Extract the media-query conditions separated with `,` (OR).
        for (i = 0; i < path.length; i++) {
            if (path[i].type !== this.type) {
                context.mediaBlocks.splice(i, 1);
                return this;
            }
            value = path[i].features instanceof value_1.default ?
                path[i].features.value : path[i].features;
            path[i] = Array.isArray(value) ? value : [value];
        }
        // Trace all permutations to generate the resulting media-query.
        //
        // (a, b and c) with nested (d, e) ->
        //    a and d
        //    a and e
        //    b and c and d
        //    b and c and e
        this.features = new value_1.default(this.permute(path).map(function (path) {
            path = path.map(function (fragment) { return fragment.toCSS ? fragment : new anonymous_1.default(fragment); });
            for (i = path.length - 1; i > 0; i--) {
                path.splice(i, 0, new anonymous_1.default('and'));
            }
            return new expression_1.default(path);
        }));
        this.setParent(this.features, this);
        // Fake a tree-node that doesn't output anything.
        return new ruleset_1.default([], []);
    },
    permute: function (arr) {
        if (arr.length === 0) {
            return [];
        }
        else if (arr.length === 1) {
            return arr[0];
        }
        else {
            var result = [];
            var rest = this.permute(arr.slice(1));
            for (var i = 0; i < rest.length; i++) {
                for (var j = 0; j < arr[0].length; j++) {
                    result.push([arr[0][j]].concat(rest[i]));
                }
            }
            return result;
        }
    },
    bubbleSelectors: function (selectors) {
        if (!selectors) {
            return;
        }
        this.rules = [new ruleset_1.default(utils.copyArray(selectors), [this.rules[0]])];
        this.setParent(this.rules, this);
    }
};
exports.default = NestableAtRulePrototype;
//# sourceMappingURL=nested-at-rule.js.map