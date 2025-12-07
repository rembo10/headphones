"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var tslib_1 = require("tslib");
var copy_anything_1 = require("copy-anything");
var declaration_1 = tslib_1.__importDefault(require("./declaration"));
var node_1 = tslib_1.__importDefault(require("./node"));
var QueryInParens = function (op, l, m, op2, r, i) {
    this.op = op.trim();
    this.lvalue = l;
    this.mvalue = m;
    this.op2 = op2 ? op2.trim() : null;
    this.rvalue = r;
    this._index = i;
    this.mvalues = [];
};
QueryInParens.prototype = Object.assign(new node_1.default(), {
    type: 'QueryInParens',
    accept: function (visitor) {
        this.lvalue = visitor.visit(this.lvalue);
        this.mvalue = visitor.visit(this.mvalue);
        if (this.rvalue) {
            this.rvalue = visitor.visit(this.rvalue);
        }
    },
    eval: function (context) {
        this.lvalue = this.lvalue.eval(context);
        var variableDeclaration;
        var rule;
        for (var i = 0; (rule = context.frames[i]); i++) {
            if (rule.type === 'Ruleset') {
                variableDeclaration = rule.rules.find(function (r) {
                    if ((r instanceof declaration_1.default) && r.variable) {
                        return true;
                    }
                    return false;
                });
                if (variableDeclaration) {
                    break;
                }
            }
        }
        if (!this.mvalueCopy) {
            this.mvalueCopy = (0, copy_anything_1.copy)(this.mvalue);
        }
        if (variableDeclaration) {
            this.mvalue = this.mvalueCopy;
            this.mvalue = this.mvalue.eval(context);
            this.mvalues.push(this.mvalue);
        }
        else {
            this.mvalue = this.mvalue.eval(context);
        }
        if (this.rvalue) {
            this.rvalue = this.rvalue.eval(context);
        }
        return this;
    },
    genCSS: function (context, output) {
        this.lvalue.genCSS(context, output);
        output.add(' ' + this.op + ' ');
        if (this.mvalues.length > 0) {
            this.mvalue = this.mvalues.shift();
        }
        this.mvalue.genCSS(context, output);
        if (this.rvalue) {
            output.add(' ' + this.op2 + ' ');
            this.rvalue.genCSS(context, output);
        }
    },
});
exports.default = QueryInParens;
//# sourceMappingURL=query-in-parens.js.map