"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var tslib_1 = require("tslib");
var node_1 = tslib_1.__importDefault(require("./node"));
var selector_1 = tslib_1.__importDefault(require("./selector"));
var ruleset_1 = tslib_1.__importDefault(require("./ruleset"));
var anonymous_1 = tslib_1.__importDefault(require("./anonymous"));
var nested_at_rule_1 = tslib_1.__importDefault(require("./nested-at-rule"));
var AtRule = function (name, value, rules, index, currentFileInfo, debugInfo, isRooted, visibilityInfo) {
    var _this = this;
    var i;
    var selectors = (new selector_1.default([], null, null, this._index, this._fileInfo)).createEmptySelectors();
    this.name = name;
    this.value = (value instanceof node_1.default) ? value : (value ? new anonymous_1.default(value) : value);
    if (rules) {
        if (Array.isArray(rules)) {
            var allDeclarations = this.declarationsBlock(rules);
            var allRulesetDeclarations_1 = true;
            rules.forEach(function (rule) {
                if (rule.type === 'Ruleset' && rule.rules)
                    allRulesetDeclarations_1 = allRulesetDeclarations_1 && _this.declarationsBlock(rule.rules, true);
            });
            if (allDeclarations && !isRooted) {
                this.simpleBlock = true;
                this.declarations = rules;
            }
            else if (allRulesetDeclarations_1 && rules.length === 1 && !isRooted && !value) {
                this.simpleBlock = true;
                this.declarations = rules[0].rules ? rules[0].rules : rules;
            }
            else {
                this.rules = rules;
            }
        }
        else {
            var allDeclarations = this.declarationsBlock(rules.rules);
            if (allDeclarations && !isRooted && !value) {
                this.simpleBlock = true;
                this.declarations = rules.rules;
            }
            else {
                this.rules = [rules];
                this.rules[0].selectors = (new selector_1.default([], null, null, index, currentFileInfo)).createEmptySelectors();
            }
        }
        if (!this.simpleBlock) {
            for (i = 0; i < this.rules.length; i++) {
                this.rules[i].allowImports = true;
            }
        }
        this.setParent(selectors, this);
        this.setParent(this.rules, this);
    }
    this._index = index;
    this._fileInfo = currentFileInfo;
    this.debugInfo = debugInfo;
    this.isRooted = isRooted || false;
    this.copyVisibilityInfo(visibilityInfo);
    this.allowRoot = true;
};
AtRule.prototype = Object.assign(new node_1.default(), tslib_1.__assign(tslib_1.__assign({ type: 'AtRule' }, nested_at_rule_1.default), { declarationsBlock: function (rules, mergeable) {
        if (mergeable === void 0) { mergeable = false; }
        if (!mergeable) {
            return rules.filter(function (node) { return (node.type === 'Declaration' || node.type === 'Comment') && !node.merge; }).length === rules.length;
        }
        else {
            return rules.filter(function (node) { return (node.type === 'Declaration' || node.type === 'Comment'); }).length === rules.length;
        }
    }, keywordList: function (rules) {
        if (!Array.isArray(rules)) {
            return false;
        }
        else {
            return rules.filter(function (node) { return (node.type === 'Keyword' || node.type === 'Comment'); }).length === rules.length;
        }
    }, accept: function (visitor) {
        var value = this.value, rules = this.rules, declarations = this.declarations;
        if (rules) {
            this.rules = visitor.visitArray(rules);
        }
        else if (declarations) {
            this.declarations = visitor.visitArray(declarations);
        }
        if (value) {
            this.value = visitor.visit(value);
        }
    }, isRulesetLike: function () {
        return this.rules || !this.isCharset();
    }, isCharset: function () {
        return '@charset' === this.name;
    }, genCSS: function (context, output) {
        var value = this.value, rules = this.rules || this.declarations;
        output.add(this.name, this.fileInfo(), this.getIndex());
        if (value) {
            output.add(' ');
            value.genCSS(context, output);
        }
        if (this.simpleBlock) {
            this.outputRuleset(context, output, this.declarations);
        }
        else if (rules) {
            this.outputRuleset(context, output, rules);
        }
        else {
            output.add(';');
        }
    }, eval: function (context) {
        var mediaPathBackup, mediaBlocksBackup, value = this.value, rules = this.rules || this.declarations;
        // media stored inside other atrule should not bubble over it
        // backpup media bubbling information
        mediaPathBackup = context.mediaPath;
        mediaBlocksBackup = context.mediaBlocks;
        // deleted media bubbling information
        context.mediaPath = [];
        context.mediaBlocks = [];
        if (value) {
            value = value.eval(context);
            if (value.value && this.keywordList(value.value)) {
                value = new anonymous_1.default(value.value.map(function (keyword) { return keyword.value; }).join(', '), this.getIndex(), this.fileInfo());
            }
        }
        if (rules) {
            rules = this.evalRoot(context, rules);
        }
        if (Array.isArray(rules) && rules[0].rules && Array.isArray(rules[0].rules) && rules[0].rules.length) {
            var allMergeableDeclarations = this.declarationsBlock(rules[0].rules, true);
            if (allMergeableDeclarations && !this.isRooted && !value) {
                var mergeRules = context.pluginManager.less.visitors.ToCSSVisitor.prototype._mergeRules;
                mergeRules(rules[0].rules);
                rules = rules[0].rules;
                rules.forEach(function (rule) { return rule.merge = false; });
            }
        }
        if (this.simpleBlock && rules) {
            rules[0].functionRegistry = context.frames[0].functionRegistry.inherit();
            rules = rules.map(function (rule) { return rule.eval(context); });
        }
        // restore media bubbling information
        context.mediaPath = mediaPathBackup;
        context.mediaBlocks = mediaBlocksBackup;
        return new AtRule(this.name, value, rules, this.getIndex(), this.fileInfo(), this.debugInfo, this.isRooted, this.visibilityInfo());
    }, evalRoot: function (context, rules) {
        var ampersandCount = 0;
        var noAmpersandCount = 0;
        var noAmpersands = true;
        var allAmpersands = false;
        if (!this.simpleBlock) {
            rules = [rules[0].eval(context)];
        }
        var precedingSelectors = [];
        if (context.frames.length > 0) {
            var _loop_1 = function (index) {
                var frame = context.frames[index];
                if (frame.type === 'Ruleset' &&
                    frame.rules &&
                    frame.rules.length > 0) {
                    if (frame && !frame.root && frame.selectors && frame.selectors.length > 0) {
                        precedingSelectors = precedingSelectors.concat(frame.selectors);
                    }
                }
                if (precedingSelectors.length > 0) {
                    var value_1 = '';
                    var output = { add: function (s) { value_1 += s; } };
                    for (var i = 0; i < precedingSelectors.length; i++) {
                        precedingSelectors[i].genCSS(context, output);
                    }
                    if (/^&+$/.test(value_1.replace(/\s+/g, ''))) {
                        noAmpersands = false;
                        noAmpersandCount++;
                    }
                    else {
                        allAmpersands = false;
                        ampersandCount++;
                    }
                }
            };
            for (var index = 0; index < context.frames.length; index++) {
                _loop_1(index);
            }
        }
        var mixedAmpersands = ampersandCount > 0 && noAmpersandCount > 0 && !allAmpersands && !noAmpersands;
        if ((this.isRooted && ampersandCount > 0 && noAmpersandCount === 0 && !allAmpersands && noAmpersands)
            || !mixedAmpersands) {
            rules[0].root = true;
        }
        return rules;
    }, variable: function (name) {
        if (this.rules) {
            // assuming that there is only one rule at this point - that is how parser constructs the rule
            return ruleset_1.default.prototype.variable.call(this.rules[0], name);
        }
    }, find: function () {
        if (this.rules) {
            // assuming that there is only one rule at this point - that is how parser constructs the rule
            return ruleset_1.default.prototype.find.apply(this.rules[0], arguments);
        }
    }, rulesets: function () {
        if (this.rules) {
            // assuming that there is only one rule at this point - that is how parser constructs the rule
            return ruleset_1.default.prototype.rulesets.apply(this.rules[0]);
        }
    }, outputRuleset: function (context, output, rules) {
        var ruleCnt = rules.length;
        var i;
        context.tabLevel = (context.tabLevel | 0) + 1;
        // Compressed
        if (context.compress) {
            output.add('{');
            for (i = 0; i < ruleCnt; i++) {
                rules[i].genCSS(context, output);
            }
            output.add('}');
            context.tabLevel--;
            return;
        }
        // Non-compressed
        var tabSetStr = "\n".concat(Array(context.tabLevel).join('  ')), tabRuleStr = "".concat(tabSetStr, "  ");
        if (!ruleCnt) {
            output.add(" {".concat(tabSetStr, "}"));
        }
        else {
            output.add(" {".concat(tabRuleStr));
            rules[0].genCSS(context, output);
            for (i = 1; i < ruleCnt; i++) {
                output.add(tabRuleStr);
                rules[i].genCSS(context, output);
            }
            output.add("".concat(tabSetStr, "}"));
        }
        context.tabLevel--;
    } }));
exports.default = AtRule;
//# sourceMappingURL=atrule.js.map