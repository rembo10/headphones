"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var tslib_1 = require("tslib");
var variable_1 = tslib_1.__importDefault(require("../tree/variable"));
var variable_2 = tslib_1.__importDefault(require("../tree/variable"));
var styleExpression = function (args) {
    var _this = this;
    args = Array.prototype.slice.call(args);
    switch (args.length) {
        case 0: throw { type: 'Argument', message: 'one or more arguments required' };
    }
    var entityList = [new variable_1.default(args[0].value, this.index, this.currentFileInfo).eval(this.context)];
    args = entityList.map(function (a) { return a.toCSS(_this.context); }).join(this.context.compress ? ',' : ', ');
    return new variable_2.default("style(".concat(args, ")"));
};
exports.default = {
    style: function () {
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
            args[_i] = arguments[_i];
        }
        try {
            return styleExpression.call(this, args);
        }
        catch (e) { }
    },
};
//# sourceMappingURL=style.js.map