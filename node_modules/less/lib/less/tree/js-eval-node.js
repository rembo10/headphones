"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var tslib_1 = require("tslib");
var node_1 = tslib_1.__importDefault(require("./node"));
var variable_1 = tslib_1.__importDefault(require("./variable"));
var JsEvalNode = function () { };
JsEvalNode.prototype = Object.assign(new node_1.default(), {
    evaluateJavaScript: function (expression, context) {
        var result;
        var that = this;
        var evalContext = {};
        if (!context.javascriptEnabled) {
            throw { message: 'Inline JavaScript is not enabled. Is it set in your options?',
                filename: this.fileInfo().filename,
                index: this.getIndex() };
        }
        expression = expression.replace(/@\{([\w-]+)\}/g, function (_, name) {
            return that.jsify(new variable_1.default("@".concat(name), that.getIndex(), that.fileInfo()).eval(context));
        });
        try {
            expression = new Function("return (".concat(expression, ")"));
        }
        catch (e) {
            throw { message: "JavaScript evaluation error: ".concat(e.message, " from `").concat(expression, "`"),
                filename: this.fileInfo().filename,
                index: this.getIndex() };
        }
        var variables = context.frames[0].variables();
        for (var k in variables) {
            // eslint-disable-next-line no-prototype-builtins
            if (variables.hasOwnProperty(k)) {
                evalContext[k.slice(1)] = {
                    value: variables[k].value,
                    toJS: function () {
                        return this.value.eval(context).toCSS();
                    }
                };
            }
        }
        try {
            result = expression.call(evalContext);
        }
        catch (e) {
            throw { message: "JavaScript evaluation error: '".concat(e.name, ": ").concat(e.message.replace(/["]/g, '\''), "'"),
                filename: this.fileInfo().filename,
                index: this.getIndex() };
        }
        return result;
    },
    jsify: function (obj) {
        if (Array.isArray(obj.value) && (obj.value.length > 1)) {
            return "[".concat(obj.value.map(function (v) { return v.toCSS(); }).join(', '), "]");
        }
        else {
            return obj.toCSS();
        }
    }
});
exports.default = JsEvalNode;
//# sourceMappingURL=js-eval-node.js.map