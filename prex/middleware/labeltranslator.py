from ..pushdown import graph
from prex.prnml import model


class LabelTranslator(object):
    def __init__(self, network):
        self.network = network
        self.mpls_labels = network.routing.collect_labels()
        self.string_to_label = {label.name: label
                                for label in self.mpls_labels}
        self.label_to_pushdown = {label: graph.Label.get_label(label.name)
                                  for label in self.mpls_labels}
        self.pushdown_mpls_labels = set(self.label_to_pushdown.values())

    def pushdown_from_mpls(self, label):
        if isinstance(label, model.NoLabel):
            return graph.SpecialLabel.bottom_of_stack()
        return self.label_to_pushdown[label]

    def mpls_from_string(self, string):
        return self.string_to_label[string]
