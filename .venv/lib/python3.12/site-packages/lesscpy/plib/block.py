# -*- coding: utf8 -*-
"""
.. module:: lesscpy.plib.block
    :synopsis: Block parse node.

    Copyright (c)
    See LICENSE for details.
.. moduleauthor:: Johann T. Mariusson <jtm@robot.is>
"""
from .node import Node
from lesscpy.lessc import utility
from lesscpy.plib.identifier import Identifier


class Block(Node):
    """ Block node. Represents one parse-block.
    Can contain property nodes or other block nodes.
    identifier {
        propertys
        inner blocks
    }
    """

    def parse(self, scope):
        """Parse block node.
        args:
            scope (Scope): Current scope
        raises:
            SyntaxError
        returns:
            self, or a list of new blocks if media queries need to be rotated
        """
        if not self.parsed:
            scope.push()
            self.name, inner = self.tokens
            scope.current = self.name
            scope.real.append(self.name)
            if not self.name.parsed:
                self.name.parse(scope)
            if not inner:
                inner = []
            inner = list(utility.flatten([p.parse(scope) for p in inner if p]))
            self.parsed = []
            self.inner = []
            # Because media queries need to be at the root in CSS, we rotate them
            # up the parse tree. More specifically, in a situation like this where
            # the current node is .foo:
            #
            #   .foo {
            #       @media print {
            #           /* ... */
            #       }
            #       .bar {
            #           /* ... */
            #       }
            #   }
            #
            # The media query is rotated out after splitting the node, resulting in
            # this tree:
            #
            #   @media print {
            #       .foo {
            #           /* ... */
            #       }
            #   }
            #   .foo {
            #       .bar {
            #           /* ... */
            #       }
            #   }
            #
            # New media queries are returned as siblings of self. If .foo is a
            # media query itself, conditions are merged. This process is recursive
            # so that media queries bubble up and split nodes along the way.
            inner_media_queries = []
            sibling_media_queries = []
            for p in inner:
                if not isinstance(p, Block):
                    self.parsed.append(p)
                # TODO: By separating in two lists (inner and inner_media_queries),
                # we change the final order of declarations.
                elif p.tokens[1] is not None and p.name.tokens[0] == '@media':
                    inner_media_queries.append(p)
                else:
                    self.inner.append(p)
            for mb in inner_media_queries:
                # If the current node is also a media query, create a merged media
                # query for each inner media query.
                if self.name.tokens[0] == '@media':
                    part_a = self.name.tokens[2:][0][0][0]
                    part_b = mb.name.tokens[2:][0]
                    cond = [
                        '@media', ' ', [
                            part_a, (' ', 'and', ' '),
                            part_b
                        ]
                    ]
                    # TODO: mb.parsed + mb.inner reorders things again
                    mb = Block([Identifier(cond), mb.parsed + mb.inner]).parse(scope)
                    sibling_media_queries += mb
                    for block in mb:
                        scope.add_block(block)
                # Otherwise, rotate inner media queries out of self.
                else:
                    cbs = Block([self.tokens[0], mb.parsed + mb.inner]).parse(scope)
                    for cb in cbs:
                        # Replace inner block contents with new block
                        new_mb = Block([mb.tokens[0], [cb]]).parse(scope)
                        sibling_media_queries += new_mb
                        for block in new_mb:
                            scope.add_block(block)
            scope.real.pop()
            scope.pop()
            if self.inner or self.parsed:
                return [self] + sibling_media_queries
            else:
                return sibling_media_queries
        else:
            return [self]

    def raw(self, clean=False):
        """Raw block name
        args:
            clean (bool): clean name
        returns:
            str
        """
        try:
            return self.tokens[0].raw(clean)
        except (AttributeError, TypeError):
            pass

    def fmt(self, fills):
        """Format block (CSS)
        args:
            fills (dict): Fill elements
        returns:
            str (CSS)
        """
        f = "%(identifier)s%(ws)s{%(nl)s%(proplist)s}%(eb)s"
        out = []
        name = self.name.fmt(fills)
        if self.parsed and any(
                p for p in self.parsed
                if str(type(p)) != "<class 'lesscpy.plib.variable.Variable'>"):
            fills.update({
                'identifier':
                name,
                'proplist':
                ''.join([p.fmt(fills) for p in self.parsed if p]),
            })
            out.append(f % fills)
        if hasattr(self, 'inner'):
            if self.name.subparse and len(self.inner) > 0:  # @media
                inner = ''.join([p.fmt(fills) for p in self.inner])
                inner = inner.replace(fills['nl'],
                                      fills['nl'] + fills['tab']).rstrip(
                                          fills['tab'])
                if not fills['nl']:
                    inner = inner.strip()
                fills.update({
                    'identifier': name,
                    'proplist': fills['tab'] + inner
                })
                out.append(f % fills)
            else:
                out.append(''.join([p.fmt(fills) for p in self.inner]))
        return ''.join(out)

    def copy(self):
        """ Return a full copy of self
        returns: Block object
        """
        name, inner = self.tokens
        if inner:
            inner = [u.copy() if u else u for u in inner]
        if name:
            name = name.copy()
        return Block([name, inner], 0)

    def copy_inner(self, scope):
        """Copy block contents (properties, inner blocks).
        Renames inner block from current scope.
        Used for mixins.
        args:
            scope (Scope): Current scope
        returns:
            list (block contents)
        """
        if self.tokens[1]:
            tokens = [u.copy() if u else u for u in self.tokens[1]]
            out = [p for p in tokens if p]
            utility.rename(out, scope, Block)
            return out
        return None
