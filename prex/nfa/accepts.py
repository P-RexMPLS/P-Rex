class VerifyVisitor(object):
    def start(self, start, final, string):
        return final in start.visit(self, string)

    def visit_epsilon_transition(self, trans, string):
        return trans.to.visit(self, string)

    def visit_transition(self, trans, string):
        if string == "" or string[0] != trans.symbol:
            return set()

        return trans.to.visit(self, string[1:])

    def visit_location(self, node, string):
        nodes = set()
        for trans in node._outgoing:
            nodes |= trans.visit(self, string)

        if string is "":
            nodes |= {node}
        return nodes
