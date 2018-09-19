from contextlib import contextmanager
from prex.util.memoized import memoized


class TerminalExpression(object):
    def __and__(self, other):
        if other is None:
            return self
        return AndExpression(self, other)

    def __iand__(self, other):
        return self.__and__(other)

    def __or__(self, other):
        if other is None:
            return self
        return OrExpression(self, other)


class TerribleExpression(TerminalExpression):
    def __init__(self, terrible):
        self.terrible = terrible

    def __str__(self):
        return f"({self.terrible})"


class EmptyExpression(TerminalExpression):
    def __and__(self, other):
        if other is None:
            return self
        if isinstance(other, str):
            return TerribleExpression(other)
        return other

    def __or__(self, other):
        if other is None:
            return self
        if isinstance(other, str):
            return TerribleExpression(other)
        return other

    def __str__(self):
        return '1 = 1'


@memoized
class AndExpression(TerminalExpression):
    def __init__(self, e1, e2):
        self._e1 = e1
        self._e2 = e2

    def __str__(self):
        try:
            return self.str
        except AttributeError:
            self.str = f"({self._e1} & {self._e2})"
            return str(self)


class OrExpression(TerminalExpression):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __str__(self):
        return f"({self.e1} | {self.e2})"


@memoized
class SetExpression(TerminalExpression):
    def __init__(self, var, value):
        self._var = var
        self._value = value

    def __str__(self):
        try:
            return self.str
        except AttributeError:
            self.str = f"({self._var}' = {self._value})"
            return str(self)


class EqExpression(TerminalExpression):
    def __init__(self, var, value):
        self.var = var
        self.value = value

    def __str__(self):
        return f"({self.var} = {self.value})"


class NotEqExpression(TerminalExpression):
    def __init__(self, var, value):
        self.var = var
        self.value = value

    def __str__(self):
        return f"({self.var} != {self.value})"


class LtExpression(TerminalExpression):
    def __init__(self, var, value):
        self.var = var
        self.value = value

    def __str__(self):
        return f"({self.var} < {self.value})"


class AddExpression(object):
    def __init__(self, var, value):
        self.var = var
        self.value = value

    def __str__(self):
        return f"{self.var} + {self.value}"


class Variable(object):
    def __init__(self, name, id_):
        self.name = name
        self.id_ = id_

    def __str__(self):
        return self.name


class Generator(object):
    def __init__(self):
        self.keepvars = set()
        self.free = [i for i in range(9, -1, -1)]
        self.used = set()

    def alloc_variable(self):
        next_ = self.free.pop()
        var = Variable(f"var_{next_}", next_)
        self.used.add(var.name)
        self.keepvars.add(var)

        return var

    @contextmanager
    def variable(self, name):
        var = self.alloc_variable()
        try:
            yield var
        finally:
            self.free_variable(var)

    def free_variable(self, var):
        self.free.append(var.id_)
        var.id_ = None
        self.keepvars.remove(var)

    def get_expression(self, explicit=None, exclude=set()):
        expression = EmptyExpression()
        expression &= explicit

        for var in self.keepvars:
            if var in exclude:
                continue
            expression &= SetExpression(var, var)

        return expression
