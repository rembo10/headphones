# mako/pyparser.py
# Copyright (C) 2006-2013 the Mako authors and contributors <see AUTHORS file>
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Handles parsing of Python code.

Parsing to AST is done via _ast on Python > 2.5, otherwise the compiler
module is used.
"""

from mako import exceptions, util, compat
from mako.compat import StringIO, arg_stringname
import operator

if compat.py3k:
    # words that cannot be assigned to (notably
    # smaller than the total keys in __builtins__)
    reserved = set(['True', 'False', 'None', 'print'])

    # the "id" attribute on a function node
    arg_id = operator.attrgetter('arg')
else:
    # words that cannot be assigned to (notably
    # smaller than the total keys in __builtins__)
    reserved = set(['True', 'False', 'None'])

    # the "id" attribute on a function node
    arg_id = operator.attrgetter('id')


try:
    import _ast
    util.restore__ast(_ast)
    from mako import _ast_util
except ImportError:
    _ast = None
    from compiler import parse as compiler_parse
    from compiler import visitor



def parse(code, mode='exec', **exception_kwargs):
    """Parse an expression into AST"""


    try:
        if _ast:
            return _ast_util.parse(code, '<unknown>', mode)
        else:
            if isinstance(code, compat.text_type):
                code = code.encode('ascii', 'backslashreplace')
            return compiler_parse(code, mode)
    except Exception:
        raise exceptions.SyntaxException(
                    "(%s) %s (%r)" % (
                        compat.exception_as().__class__.__name__,
                        compat.exception_as(),
                        code[0:50]
                    ), **exception_kwargs)


if _ast:
    class FindIdentifiers(_ast_util.NodeVisitor):

        def __init__(self, listener, **exception_kwargs):
            self.in_function = False
            self.in_assign_targets = False
            self.local_ident_stack = set()
            self.listener = listener
            self.exception_kwargs = exception_kwargs

        def _add_declared(self, name):
            if not self.in_function:
                self.listener.declared_identifiers.add(name)
            else:
                self.local_ident_stack.add(name)

        def visit_ClassDef(self, node):
            self._add_declared(node.name)

        def visit_Assign(self, node):

            # flip around the visiting of Assign so the expression gets
            # evaluated first, in the case of a clause like "x=x+5" (x
            # is undeclared)

            self.visit(node.value)
            in_a = self.in_assign_targets
            self.in_assign_targets = True
            for n in node.targets:
                self.visit(n)
            self.in_assign_targets = in_a

        if compat.py3k:

            # ExceptHandler is in Python 2, but this block only works in
            # Python 3 (and is required there)

            def visit_ExceptHandler(self, node):
                if node.name is not None:
                    self._add_declared(node.name)
                if node.type is not None:
                    self.listener.undeclared_identifiers.add(node.type.id)
                for statement in node.body:
                    self.visit(statement)

        def visit_Lambda(self, node, *args):
            self._visit_function(node, True)

        def visit_FunctionDef(self, node):
            self._add_declared(node.name)
            self._visit_function(node, False)

        def _expand_tuples(self, args):
            for arg in args:
                if isinstance(arg, _ast.Tuple):
                    for n in arg.elts:
                        yield n
                else:
                    yield arg

        def _visit_function(self, node, islambda):

            # push function state onto stack.  dont log any more
            # identifiers as "declared" until outside of the function,
            # but keep logging identifiers as "undeclared". track
            # argument names in each function header so they arent
            # counted as "undeclared"

            inf = self.in_function
            self.in_function = True

            local_ident_stack = self.local_ident_stack
            self.local_ident_stack = local_ident_stack.union([
                arg_id(arg) for arg in self._expand_tuples(node.args.args)
            ])
            if islambda:
                self.visit(node.body)
            else:
                for n in node.body:
                    self.visit(n)
            self.in_function = inf
            self.local_ident_stack = local_ident_stack

        def visit_For(self, node):

            # flip around visit

            self.visit(node.iter)
            self.visit(node.target)
            for statement in node.body:
                self.visit(statement)
            for statement in node.orelse:
                self.visit(statement)

        def visit_Name(self, node):
            if isinstance(node.ctx, _ast.Store):
                # this is eqiuvalent to visit_AssName in
                # compiler
                self._add_declared(node.id)
            elif node.id not in reserved and node.id \
                not in self.listener.declared_identifiers and node.id \
                not in self.local_ident_stack:
                self.listener.undeclared_identifiers.add(node.id)

        def visit_Import(self, node):
            for name in node.names:
                if name.asname is not None:
                    self._add_declared(name.asname)
                else:
                    self._add_declared(name.name.split('.')[0])

        def visit_ImportFrom(self, node):
            for name in node.names:
                if name.asname is not None:
                    self._add_declared(name.asname)
                else:
                    if name.name == '*':
                        raise exceptions.CompileException(
                          "'import *' is not supported, since all identifier "
                          "names must be explicitly declared.  Please use the "
                          "form 'from <modulename> import <name1>, <name2>, "
                          "...' instead.", **self.exception_kwargs)
                    self._add_declared(name.name)


    class FindTuple(_ast_util.NodeVisitor):

        def __init__(self, listener, code_factory, **exception_kwargs):
            self.listener = listener
            self.exception_kwargs = exception_kwargs
            self.code_factory = code_factory

        def visit_Tuple(self, node):
            for n in node.elts:
                p = self.code_factory(n, **self.exception_kwargs)
                self.listener.codeargs.append(p)
                self.listener.args.append(ExpressionGenerator(n).value())
                self.listener.declared_identifiers = \
                    self.listener.declared_identifiers.union(
                                                    p.declared_identifiers)
                self.listener.undeclared_identifiers = \
                    self.listener.undeclared_identifiers.union(
                                                    p.undeclared_identifiers)


    class ParseFunc(_ast_util.NodeVisitor):

        def __init__(self, listener, **exception_kwargs):
            self.listener = listener
            self.exception_kwargs = exception_kwargs

        def visit_FunctionDef(self, node):
            self.listener.funcname = node.name
            argnames = [arg_id(arg) for arg in node.args.args]
            if node.args.vararg:
                argnames.append(arg_stringname(node.args.vararg))
            if node.args.kwarg:
                argnames.append(arg_stringname(node.args.kwarg))
            self.listener.argnames = argnames
            self.listener.defaults = node.args.defaults  # ast
            self.listener.varargs = node.args.vararg
            self.listener.kwargs = node.args.kwarg

    class ExpressionGenerator(object):

        def __init__(self, astnode):
            self.generator = _ast_util.SourceGenerator(' ' * 4)
            self.generator.visit(astnode)

        def value(self):
            return ''.join(self.generator.result)
else:
    class FindIdentifiers(object):

        def __init__(self, listener, **exception_kwargs):
            self.in_function = False
            self.local_ident_stack = set()
            self.listener = listener
            self.exception_kwargs = exception_kwargs

        def _add_declared(self, name):
            if not self.in_function:
                self.listener.declared_identifiers.add(name)
            else:
                self.local_ident_stack.add(name)

        def visitClass(self, node, *args):
            self._add_declared(node.name)

        def visitAssName(self, node, *args):
            self._add_declared(node.name)

        def visitAssign(self, node, *args):

            # flip around the visiting of Assign so the expression gets
            # evaluated first, in the case of a clause like "x=x+5" (x
            # is undeclared)
            self.visit(node.expr, *args)
            for n in node.nodes:
                self.visit(n, *args)

        def visitLambda(self, node, *args):
            self._visit_function(node, args)

        def visitFunction(self, node, *args):
            self._add_declared(node.name)
            self._visit_function(node, args)

        def _expand_tuples(self, args):
            for arg in args:
                if isinstance(arg, tuple):
                    for n in arg:
                        yield n
                else:
                    yield arg

        def _visit_function(self, node, args):

            # push function state onto stack.  dont log any more
            # identifiers as "declared" until outside of the function,
            # but keep logging identifiers as "undeclared". track
            # argument names in each function header so they arent
            # counted as "undeclared"

            inf = self.in_function
            self.in_function = True

            local_ident_stack = self.local_ident_stack
            self.local_ident_stack = local_ident_stack.union([
                arg for arg in self._expand_tuples(node.argnames)
            ])

            for n in node.getChildNodes():
                self.visit(n, *args)
            self.in_function = inf
            self.local_ident_stack = local_ident_stack

        def visitFor(self, node, *args):

            # flip around visit

            self.visit(node.list, *args)
            self.visit(node.assign, *args)
            self.visit(node.body, *args)

        def visitName(self, node, *args):
            if node.name not in reserved and node.name \
                not in self.listener.declared_identifiers and node.name \
                not in self.local_ident_stack:
                self.listener.undeclared_identifiers.add(node.name)

        def visitImport(self, node, *args):
            for mod, alias in node.names:
                if alias is not None:
                    self._add_declared(alias)
                else:
                    self._add_declared(mod.split('.')[0])

        def visitFrom(self, node, *args):
            for mod, alias in node.names:
                if alias is not None:
                    self._add_declared(alias)
                else:
                    if mod == '*':
                        raise exceptions.CompileException(
                        "'import *' is not supported, since all identifier "
                        "names must be explicitly declared.  Please use the "
                        "form 'from <modulename> import <name1>, <name2>, "
                        "...' instead.", **self.exception_kwargs)
                    self._add_declared(mod)

        def visit(self, expr):
            visitor.walk(expr, self)  # , walker=walker())


    class FindTuple(object):

        def __init__(self, listener, code_factory, **exception_kwargs):
            self.listener = listener
            self.exception_kwargs = exception_kwargs
            self.code_factory = code_factory

        def visitTuple(self, node, *args):
            for n in node.nodes:
                p = self.code_factory(n, **self.exception_kwargs)
                self.listener.codeargs.append(p)
                self.listener.args.append(ExpressionGenerator(n).value())
                self.listener.declared_identifiers = \
                    self.listener.declared_identifiers.union(
                                                      p.declared_identifiers)
                self.listener.undeclared_identifiers = \
                    self.listener.undeclared_identifiers.union(
                                                      p.undeclared_identifiers)

        def visit(self, expr):
            visitor.walk(expr, self)  # , walker=walker())


    class ParseFunc(object):

        def __init__(self, listener, **exception_kwargs):
            self.listener = listener
            self.exception_kwargs = exception_kwargs

        def visitFunction(self, node, *args):
            self.listener.funcname = node.name
            self.listener.argnames = node.argnames
            self.listener.defaults = node.defaults
            self.listener.varargs = node.varargs
            self.listener.kwargs = node.kwargs

        def visit(self, expr):
            visitor.walk(expr, self)


    class ExpressionGenerator(object):

        """given an AST node, generates an equivalent literal Python
        expression."""

        def __init__(self, astnode):
            self.buf = StringIO()
            visitor.walk(astnode, self)  # , walker=walker())

        def value(self):
            return self.buf.getvalue()

        def operator(self, op, node, *args):
            self.buf.write('(')
            self.visit(node.left, *args)
            self.buf.write(' %s ' % op)
            self.visit(node.right, *args)
            self.buf.write(')')

        def booleanop(self, op, node, *args):
            self.visit(node.nodes[0])
            for n in node.nodes[1:]:
                self.buf.write(' ' + op + ' ')
                self.visit(n, *args)

        def visitConst(self, node, *args):
            self.buf.write(repr(node.value))

        def visitAssName(self, node, *args):

            # TODO: figure out OP_ASSIGN, other OP_s

            self.buf.write(node.name)

        def visitName(self, node, *args):
            self.buf.write(node.name)

        def visitMul(self, node, *args):
            self.operator('*', node, *args)

        def visitAnd(self, node, *args):
            self.booleanop('and', node, *args)

        def visitOr(self, node, *args):
            self.booleanop('or', node, *args)

        def visitBitand(self, node, *args):
            self.booleanop('&', node, *args)

        def visitBitor(self, node, *args):
            self.booleanop('|', node, *args)

        def visitBitxor(self, node, *args):
            self.booleanop('^', node, *args)

        def visitAdd(self, node, *args):
            self.operator('+', node, *args)

        def visitGetattr(self, node, *args):
            self.visit(node.expr, *args)
            self.buf.write('.%s' % node.attrname)

        def visitSub(self, node, *args):
            self.operator('-', node, *args)

        def visitNot(self, node, *args):
            self.buf.write('not ')
            self.visit(node.expr)

        def visitDiv(self, node, *args):
            self.operator('/', node, *args)

        def visitFloorDiv(self, node, *args):
            self.operator('//', node, *args)

        def visitSubscript(self, node, *args):
            self.visit(node.expr)
            self.buf.write('[')
            [self.visit(x) for x in node.subs]
            self.buf.write(']')

        def visitUnarySub(self, node, *args):
            self.buf.write('-')
            self.visit(node.expr)

        def visitUnaryAdd(self, node, *args):
            self.buf.write('-')
            self.visit(node.expr)

        def visitSlice(self, node, *args):
            self.visit(node.expr)
            self.buf.write('[')
            if node.lower is not None:
                self.visit(node.lower)
            self.buf.write(':')
            if node.upper is not None:
                self.visit(node.upper)
            self.buf.write(']')

        def visitDict(self, node):
            self.buf.write('{')
            c = node.getChildren()
            for i in range(0, len(c), 2):
                self.visit(c[i])
                self.buf.write(': ')
                self.visit(c[i + 1])
                if i < len(c) - 2:
                    self.buf.write(', ')
            self.buf.write('}')

        def visitTuple(self, node):
            self.buf.write('(')
            c = node.getChildren()
            for i in range(0, len(c)):
                self.visit(c[i])
                if i < len(c) - 1:
                    self.buf.write(', ')
            self.buf.write(')')

        def visitList(self, node):
            self.buf.write('[')
            c = node.getChildren()
            for i in range(0, len(c)):
                self.visit(c[i])
                if i < len(c) - 1:
                    self.buf.write(', ')
            self.buf.write(']')

        def visitListComp(self, node):
            self.buf.write('[')
            self.visit(node.expr)
            self.buf.write(' ')
            for n in node.quals:
                self.visit(n)
            self.buf.write(']')

        def visitListCompFor(self, node):
            self.buf.write(' for ')
            self.visit(node.assign)
            self.buf.write(' in ')
            self.visit(node.list)
            for n in node.ifs:
                self.visit(n)

        def visitListCompIf(self, node):
            self.buf.write(' if ')
            self.visit(node.test)

        def visitCompare(self, node):
            self.visit(node.expr)
            for tup in node.ops:
                self.buf.write(tup[0])
                self.visit(tup[1])

        def visitCallFunc(self, node, *args):
            self.visit(node.node)
            self.buf.write('(')
            if len(node.args):
                self.visit(node.args[0])
                for a in node.args[1:]:
                    self.buf.write(', ')
                    self.visit(a)
            self.buf.write(')')

        def visitLambda(self, node, *args):
            self.buf.write('lambda ')

            argnames = list(node.argnames)

            kw = arg = None
            if node.kwargs > 0:
                kw = argnames.pop(-1)
            if node.varargs > 0:
                arg = argnames.pop(-1)

            if arg:
                argnames.append("*%s" % arg)
            if kw:
                argnames.append("**%s" % kw)

            self.buf.write(", ".join(argnames))

            self.buf.write(': ')
            self.visit(node.code)


    class walker(visitor.ASTVisitor):

        def dispatch(self, node, *args):
            print('Node:', str(node))

            # print "dir:", dir(node)

            return visitor.ASTVisitor.dispatch(self, node, *args)
