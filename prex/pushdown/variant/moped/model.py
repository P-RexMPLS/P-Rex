# @CLEANUP: This file is generally of varying relation to moped.
import contextlib


def emit_transition_group_start(f, title, header=None):
    # return
    if header:
        for line in header.splitlines():
            f.write(f"# {line}\n")
    f.write(f"# ---------{title}--------- {{{{{{\n")


def emit_transition_group_end(f):
    # return
    f.write("# }}}\n")


@contextlib.contextmanager
def emit_transition_group(f, title, header=None):
    emit_transition_group_start(f, title, header)
    yield
    emit_transition_group_end(f)


def emit_system_start(f, variables, initial, final, start_label, end_label):
    #f.write(f"global int {variables};\n")
    f.write("(")
    f.write(initial)
    f.write("<")
    f.write(start_label)
    f.write(">) # --> ")
    f.write(final)
    f.write("<")
    f.write(end_label)
    f.write(">\n")


def emit_comments(f, comments):
    # return
    for comment in comments:
        for line in comment.splitlines():
            f.write("#")
            f.write(line)
            f.write("\n")


def emit_transition(f, from_, inlabel, to, outlabel1=None, outlabel2=None,
                    text=None, expr=None):
    f.write(from_)
    f.write("<")
    f.write(inlabel)
    f.write("> --> ")
    f.write(to)
    f.write("<")
    if outlabel1 is not None:
        f.write(outlabel1)
    if outlabel2 is not None:
        f.write(" ")
        f.write(outlabel2)
    f.write(">")
    if text is not None:
        f.write(" ")
        f.write('"')
        f.write(text)
        f.write('"')
    if expr is not None:
        f.write(" ")
        f.write(expr)
    f.write("\n")


class System(object):
    def __init__(self, f, size, final, final_label, mapping,
                 transition_mapping):
        self.str = f.getvalue()
        self.size = size
        self.final = final
        self.final_label = final_label
        self.mapping = mapping
        self.transition_mapping = transition_mapping
