from . import graph
from . import expression
from prex.prnml import model


class GraphHolder(object):
    def __init__(self):
        self.node = {}

    def get_node(self, key):
        if key not in self.node:
            self.node[key] = graph.Location(
                key
            )
        return self.node[key]


# @CLEANUP: The functions here really belong in the two classes in
# .converter.*. This should be completely rolled into them.
class GraphBuilder(object):
    def __init__(self, holder, expgen):
        self.holder = holder
        self.expgen = expgen

    def epsilon_buildstep(self, enter_node, exit_node, in_label_domain, out_label):
        graph.EpsilonTransition(
            enter_node,
            exit_node,
            in_label_domain,
            graph.PushAction(out_label),
            guard=graph.Guard(self.expgen.get_expression())
        ).attach()

    def buildstep(self, enter_node, exit_node, in_label, out_label):
        graph.Transition(
            enter_node,
            exit_node,
            in_label,
            graph.PushAction(out_label),
            guard=graph.Guard(self.expgen.get_expression())
        ).attach()

    def epsilon_destroystep(self, enter_node, exit_node, labels):
        graph.EpsilonTransition(
            enter_node,
            exit_node,
            labels,
            graph.PopAction(),
            guard=graph.Guard(self.expgen.get_expression())
        ).attach()

    def destroystep(self, enter_node, exit_node, label):
        graph.Transition(
            enter_node,
            exit_node,
            label,
            graph.PopAction(),
            guard=graph.Guard(self.expgen.get_expression())
        ).attach()

    def epsilon_destroyenter(self, var, switch, interface, fails, labels, querylen):
        enterNode = self.holder.get_node(
            f"{switch.name}_{interface.name}_{fails}"
        )
        exitNode = self.holder.get_node("simend")

        exp = expression.EqExpression(var, querylen)

        graph.EpsilonTransition(
            enterNode, exitNode,
            labels,
            graph.NoopAction(),
            guard=graph.Guard(self.expgen.get_expression(
                explicit=exp,
                exclude=(var, )
            ))
        ).attach()

    def destroyenter(self, var, switch, interface, fails, label, querylen):
        enterNode = self.holder.get_node(
            f"{switch.name}_{interface.name}_{fails}"
        )
        exitNode = self.holder.get_node("simend")

        exp = expression.EqExpression(var, querylen)

        graph.Transition(
            enterNode, exitNode,
            label,
            graph.NoopAction(),
            guard=graph.Guard(self.expgen.get_expression(
                explicit=exp,
                exclude=(var, )
            ))
        ).attach()

    def destroyexit(self, enter_node):
        # @HACK: We should store the complete node somewhere as well
        exit_node = self.holder.get_node('complete')

        graph.Transition(enter_node,
                         exit_node,
                         graph.SpecialLabel.bottom_of_stack(),
                         graph.NoopAction(),
                         guard=graph.Guard(self.expgen.get_expression())
        ).attach()

    def epsilon_startsim(self, var, node_var, switch, interface, labels):
        enterNode = self.holder.get_node(f"simstart")
        exitNode = self.holder.get_node(f"{switch.name}_{interface.name}")

        exp = (expression.SetExpression(var, 0)
               & expression.SetExpression(node_var, 0))

        graph.EpsilonTransition(
            enterNode, exitNode,
            labels,
            graph.NoopAction(),
            guard=graph.Guard(self.expgen.get_expression(
                explicit=exp,
                exclude=(var, node_var)
            ))
        ).attach()

    def startsim(self, var, node_var, switch, interface, label):
        enterNode = self.holder.get_node(f"simstart")
        exitNode = self.holder.get_node(f"{switch.name}_{interface.name}")

        exp = (expression.SetExpression(var, 0)
               & expression.SetExpression(node_var, 0))

        graph.Transition(
            enterNode, exitNode,
            label,
            graph.NoopAction(),
            guard=graph.Guard(self.expgen.get_expression(
                explicit=exp,
                exclude=(var, node_var)
            ))
        ).attach()

    def epsilon_linkconnect(self, from_, to, fails, labels, node_var):
        enterNode = self.holder.get_node(
            f"{from_.switch.name}_{from_.interface.name}_{fails}"
        )
        exitNode = self.holder.get_node(
            f"{to.switch.name}_{to.interface.name}"
        )

        exp = expression.SetExpression(node_var, 0)

        graph.EpsilonTransition(
            enterNode, exitNode,
            labels,
            graph.NoopAction(),
            guard=graph.Guard(self.expgen.get_expression(
                explicit=exp,
                exclude=(node_var, )
            ))
        ).attach()

    def linkconnect(self, from_, to, fails, label, node_var):
        enterNode = self.holder.get_node(
            f"{from_.switch.name}_{from_.interface.name}_{fails}"
        )
        exitNode = self.holder.get_node(
            f"{to.switch.name}_{to.interface.name}"
        )

        exp = expression.SetExpression(node_var, 0)

        graph.Transition(
            enterNode, exitNode,
            label,
            graph.NoopAction(),
            guard=graph.Guard(self.expgen.get_expression(
                explicit=exp,
                exclude=(node_var, )
            ))
        ).attach()

    def query_linkconnect(self, var, from_, to, fails, label, index):
        enterNode = self.holder.get_node(
            f"{from_.switch.name}_{from_.interface.name}_{fails}"
        )
        exitNode = self.holder.get_node(
            f"{to.switch.name}_{to.interface.name}"
        )

        graph.Transition(
            enterNode, exitNode,
            label,
            graph.NoopAction(),
            guard=graph.Guard(self.expgen.get_expression(
                explicit=(
                    f"{var.name} = {index} & {var.name}' = {var.name} + 1"
                ),
                exclude=(var,)
            ))
        ).attach()

    def epsilon_input_loop(self, switch, interface, labels, node_var, var, step):
        node = self.holder.get_node(
            f"{switch.name}_{interface.name}"
        )

        exp = (expression.EqExpression(var, step)
               & expression.SetExpression(node_var, 1)
               & expression.EqExpression(node_var, 0))

        graph.EpsilonTransition(
            node, node,
            labels,
            graph.NoopAction(),
            guard=graph.Guard(self.expgen.get_expression(
                explicit=(
                    exp
                ),
                exclude=(node_var,)
            ))
        ).attach()

    def input_loop(self, switch, interface, label, node_var, var, step):
        node = self.holder.get_node(
            f"{switch.name}_{interface.name}"
        )

        exp = (expression.EqExpression(var, step)
               & expression.SetExpression(node_var, 1)
               & expression.EqExpression(node_var, 0))

        graph.Transition(
            node, node,
            label,
            graph.NoopAction(),
            guard=graph.Guard(self.expgen.get_expression(
                explicit=(
                    exp
                ),
                exclude=(node_var,)
            ))
        ).attach()

    def epsilon_output_loop(self, switch, interface, fails, labels, node_var, var, step):  # noqa
        node = self.holder.get_node(
            f"{switch.name}_{interface.name}_{fails}"
        )

        exp = (expression.SetExpression(var, expression.AddExpression(var, 1))
               & expression.SetExpression(node_var, 2)
               & expression.EqExpression(node_var, 1))

        graph.EpsilonTransition(
            node, node,
            labels,
            graph.NoopAction(),
            guard=graph.Guard(self.expgen.get_expression(
                explicit=(
                    exp
                ),
                exclude=(node_var, var)
            ))
        ).attach()

    def output_loop(self, switch, interface, fails, label, node_var, var, step):  # noqa
        node = self.holder.get_node(
            f"{switch.name}_{interface.name}_{fails}"
        )

        exp = (expression.SetExpression(var, expression.AddExpression(var, 1))
               & expression.SetExpression(node_var, 2)
               & expression.EqExpression(node_var, 1))

        graph.Transition(
            node, node,
            label,
            graph.NoopAction(),
            guard=graph.Guard(self.expgen.get_expression(
                explicit=(
                    exp
                ),
                exclude=(node_var, var)
            ))
        ).attach()

    def routing(self, switch, from_, to, label, actions, label_domain):
        enterNode = self.holder.get_node(f"{switch.name}_{from_.name}")
        exitNode = self.holder.get_node(f"{switch.name}_{to.name}_{0}")
        labels = (label,)

        for i in range(1, len(actions)):
            # Create extra node to perform the op
            node = self.holder.get_node(f"{switch.name}_{i}_{from_.name}")
            for _label in labels:
                graph.Transition(
                    enterNode,
                    node,
                    _label,
                    actions[i].to_graph(),
                    guard=graph.Guard(self.expgen.get_expression())
                ).attach()
                enterNode = node
            if (isinstance(actions[i], model.PushAction) or
                isinstance(actions[i], model.SwapAction)):
                # Set the set of labels to match to the label we pushed or swapped to
                labels = (graph.Label.get_label(actions[i].label),)
            elif isinstance(actions[i], model.PopAction):
                # For pop we do not know what is underneath, must set to entire domain
                labels = label_domain
            elif isinstance(actions[i], model.NoopAction):
                # Don't need to modify labels, nothing to do
                pass
            else:
                # How?
                raise RuntimeError('Unknown action')

        # Connect the chain to the actual exitNode
        for _label in labels:
            graph.Transition(
                enterNode,
                exitNode,
                _label,
                actions[0].to_graph(),
                guard=graph.Guard(self.expgen.get_expression())
            ).attach()

    def protection(self, switch, from_, to, fails, label, actions, node_var, label_domain):
        enterNode = self.holder.get_node(
            f"{switch.name}_{from_.name}_{fails}"
        )
        exitNode = self.holder.get_node(
            f"{switch.name}_{to.name}_{fails + 1}"
        )
        labels = (label,)

        for i in range(1, len(actions)):
            # Create extra node to perform the op
            node = self.holder.get_node(f"{switch.name}_{i}_{from_.name}_{fails}")
            for _label in labels:
                graph.Transition(
                    enterNode,
                    node,
                    _label,
                    actions[i].to_graph(),
                    guard=graph.Guard(self.expgen.get_expression())
                ).attach()
                enterNode = node
            if (isinstance(actions[i], model.PushAction) or
                isinstance(actions[i], model.SwapAction)):
                # Set the set of labels to match to the label we pushed or swapped to
                labels = (graph.Label.get_label(actions[i].label),)
            elif isinstance(actions[i], model.PopAction):
                # For pop we do not know what is underneath, must set to entire domain
                labels = label_domain
            elif isinstance(actions[i], model.NoopAction):
                # Don't need to modify labels, nothing to do
                pass
            else:
                # How?
                raise RuntimeError('Unknown action')

        # Connect the chain to the actual exitNode
        # and apply the failover condition here for simplicity
        exp = expression.NotEqExpression(node_var, 2)
        for _label in labels:
            graph.Transition(
                enterNode,
                exitNode,
                _label,
                actions[0].to_graph(),
                guard=graph.Guard(self.expgen.get_expression(
                    explicit=exp,
                    exclude=(node_var,)
                ))
            ).attach()
