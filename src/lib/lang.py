from __future__ import annotations

from typing import TypeVar, Generic, Any, Union, Optional, Tuple
from typing_extensions import Protocol

from src.lib.bitcoinlib.static_types import *
from .bitcoinlib.script import CScript
from .opcodes import Op
from .util import *



class ClauseProtocol(Protocol):
    @property
    def a(self) -> Any:
        pass
    @property
    def b(self) -> Any:
        pass
    @property
    def n_args(self) -> int:
        return 0
    @property
    def symbol(self) -> str:
        return ""

class StringClauseMixin:
    MODE = "+"  # "str"
    def __str__(self: ClauseProtocol) -> str:
        if StringClauseMixin.MODE == "+":
            if self.__class__.n_args == 1:
                return "{}({})".format(self.__class__.__name__, self.a)
            elif self.__class__.n_args == 2:
                return "{}{}{}".format(self.a, self.symbol, self.b)
            else:
                return "{}()".format(self.__class__.__name__)
        else:
            if self.__class__.n_args == 1:
                return "{}({})".format(self.__class__.__name__, self.a)
            elif self.__class__.n_args == 2:
                return "{}({}, {})".format(self.__class__.__name__, self.a, self.b)
            else:
                return "{}()".format(self.__class__.__name__)


class SatisfiedClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 0
class UnsatisfiableClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 0


class AndClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 2
    symbol = "*"

    def __init__(self, a: AndClauseArgument, b: AndClauseArgument):
        self.a = a
        self.b = b


class OrClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 2
    symbol = "+"
    def __init__(self, a: AndClauseArgument, b: AndClauseArgument):
        self.a: AndClauseArgument = a
        self.b: AndClauseArgument = b


class SignatureCheckClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 1
    def __init__(self, a: Variable[PubKey]):
        self.a = a
        self.b = a.sub_variable("signature")


class PreImageCheckClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 1

    a : Variable[Hash]
    b : Variable[Hash]
    def __init__(self, a: Variable[Hash]):
        self.a = a
        self.b = a.sub_variable("preimage")


class CheckTemplateVerifyClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 1

    def __init__(self, a: Variable[Hash]):
        self.a = a



class AbsoluteTimeSpec:
    def __init__(self, t):
        self.time = t


class RelativeTimeSpec:
    def __init__(self, t):
        self.time = t


TimeSpec = Union[AbsoluteTimeSpec, RelativeTimeSpec]

def Weeks(n):
    return Variable("RelativeTimeSpec({} Weeks)".format(n), RelativeTimeSpec(n))


class AfterClause(StringClauseMixin):
    def __add__(self, other: AndClauseArgument) -> OrClause:
        return OrClause(self, other)

    def __mul__(self, other: AndClauseArgument) -> AndClause:
        return AndClause(self, other)
    n_args = 1

    def __init__(self, a: Variable[TimeSpec]):
        self.a = a


V = TypeVar('V')


class Variable(Generic[V]):
    def __init__(self, name: str, value: Optional[V] = None):
        self.name: str = name
        self.value: Optional[V] = value
        self.sub_variable_count = -1

    def sub_variable(self, purpose: str, value: Optional[V] = None) -> Variable:
        self.sub_variable_count += 1
        return Variable(self.name + "_" + str(self.sub_variable_count) + "_" + purpose, value)

    def assign(self, value: V):
        self.value = value

    def __str__(self):
        return "{}('{}', {})".format(self.__class__.__name__, self.name, self.value)


AndClauseArgument = Union[
               SatisfiedClause,
               UnsatisfiableClause,
               OrClause,
               AndClause,
               SignatureCheckClause,
               PreImageCheckClause,
               CheckTemplateVerifyClause,
               AfterClause]
Clause = Union[SatisfiedClause, UnsatisfiableClause,
               Variable,
               OrClause,
               AndClause,
               SignatureCheckClause,
               PreImageCheckClause,
               CheckTemplateVerifyClause,
               AfterClause]

T = TypeVar('T')


class ProgramBuilder:

    def bind(self, variable: Variable[T], value: T):
        pass

    def compile_cnf(self, clause: Clause) -> List[List[Clause]]:
        # TODO: Figure out how many passes are required / abort when stable
        # 1000 should be enough that covers all valid scripts...
        for x in range(1000):
            clause = self.normalize(clause)
        return self.flatten(clause)

    class WitnessTemplate:
        def __init__(self):
            self.witness = []
            self.nickname = None
        def add(self, it):
            self.witness.insert(0, it)
        def name(self, nickname):
            self.nickname = nickname
    def compile(self, clause: Clause) -> Tuple[CScript, List[Any]]:
        cnf: List[List[Clause]] = self.compile_cnf(clause)
        n_cases = len(cnf)
        witnesses : List[ProgramBuilder.WitnessTemplate] = [ProgramBuilder.WitnessTemplate() for  _ in cnf]
        script = CScript()
        # If we have one or two cases, special case the emitted scripts
        # 3 or more, use a generic wrapper
        if n_cases == 1:
            for cl in cnf[0]:
                compiled_frag = self._compile(cl, witnesses[0])
                script += compiled_frag
            # Hack because the fragment compiler leaves stack empty
            script += CScript([1])
        elif n_cases == 2:
            witnesses[0].add(1)
            witnesses[1].add(0)
            # note order of side effects!
            branch_a = CScript([self._compile(frag, witnesses[0]) for frag in cnf[0]])
            branch_b = CScript([self._compile(frag, witnesses[1]) for frag in cnf[1]])
            script = CScript([Op.If,
                               branch_a,
                               Op.Else,
                               branch_b,
                               Op.EndIf,
                               1])
        else:
            # Check that the first argument passed is an in range execution path
            script = CScript([Op.Dup, 0, n_cases, Op.Within, Op.Verify])
            for (idx, frag) in enumerate(cnf):
                witnesses[idx].add(idx + 1)
                script += CScript([Op.SubOne, Op.IfDup, Op.NotIf])

                for cl in frag:
                    script += self._compile(cl, witnesses[idx])
                script += CScript([Op.Zero,  Op.EndIf])
        return script, witnesses

    # Normalize Bubbles up all the OR clauses into a CNF
    @methdispatch
    def normalize(self, arg: Clause) -> Clause:
        raise NotImplementedError("Cannot Compile Arg")

    @normalize.register
    def normalize_and(self, arg: AndClause) -> Clause:
        a :AndClauseArgument = arg.a
        b: AndClauseArgument = arg.b
        if isinstance(a, OrClause) and isinstance(b, OrClause):
            a0: AndClauseArgument = a.a
            a1: AndClauseArgument = a.b
            b0: AndClauseArgument = b.a
            b1: AndClauseArgument = b.b
            return a0*b0 + a0*b1 + a1*b0 + a1*b1
        elif isinstance(b, AndClause) and isinstance(a, OrClause):
            _or, _and = a, b
            return _and * _or.a + _and * _or.b
        elif isinstance(a, AndClause) and isinstance(b, OrClause):
            _or, _and = b, a
            return _and * _or.a + _and * _or.b
        # Other Clause can be ignored...
        elif isinstance(a, AndClause):
            return AndClause(self.normalize(a), b)
        elif isinstance(a, OrClause):
            a0, a1 = a.a, a.b
            return a0*b + a1*b
        elif isinstance(b, AndClause):
            return AndClause(self.normalize(b), a)
        elif isinstance(b, OrClause):
            b0, b1 = b.a, b.b
            return b0*a + b1*a
        else:
            return arg

    @normalize.register
    def normalize_or(self, arg: OrClause) -> Clause:
        return OrClause(self.normalize(arg.a), self.normalize(arg.b))

    # TODO: Unionize!

    @normalize.register
    def normalize_signaturecheck(self, arg: SignatureCheckClause) -> Clause:
        return arg

    @normalize.register
    def normalize_preimagecheck(self, arg: PreImageCheckClause) -> Clause:
        return arg

    @normalize.register
    def normalize_ctv(self, arg: CheckTemplateVerifyClause) -> Clause:
        return arg

    @normalize.register
    def normalize_after(self, arg: AfterClause) -> Clause:
        return arg

    @normalize.register
    def normalize_var(self, arg: Variable) -> Clause:
        return arg

    @methdispatch
    def flatten(self, arg: Clause) -> List[List[Clause]]:
        raise NotImplementedError("Cannot Compile Arg")

    @flatten.register
    def flatten_and(self, arg: AndClause) -> List[List[Clause]]:
        assert not isinstance(arg.a, OrClause)
        assert not isinstance(arg.b, OrClause)
        l = self.flatten(arg.a)
        l2 = self.flatten(arg.b)
        assert len(l) == 1
        assert len(l2) == 1
        l[0].extend(l2[0])
        return l

    @flatten.register
    def flatten_or(self, arg: OrClause) -> List[List[Clause]]:
        return self.flatten(arg.a) + self.flatten(arg.b)

    @flatten.register
    def flatten_sigcheck(self, arg: SignatureCheckClause) -> List[List[Clause]]:
        return [[arg]]

    @flatten.register
    def flatten_preimage(self, arg: PreImageCheckClause) -> List[List[Clause]]:
        return [[arg]]

    @flatten.register
    def flatten_ctv(self, arg: CheckTemplateVerifyClause) -> List[List[Clause]]:
        return [[arg]]

    @flatten.register
    def flatten_after(self, arg: AfterClause) -> List[List[Clause]]:
        return [[arg]]

    @flatten.register
    def flatten_var(self, arg: Variable) -> List[List[Clause]]:
        return [[arg]]

    @methdispatch
    def _compile(self, arg: Clause, witness : ProgramBuilder.WitnessTemplate) -> CScript:
        raise NotImplementedError("Cannot Compile Arg", arg)

    @_compile.register
    def _compile_and(self, arg: SignatureCheckClause, witness) -> CScript:
        return self._compile(arg.b, witness) + self._compile(arg.a, witness) + CScript([Op.Check_sig_verify])

    @_compile.register
    def _compile_preimage(self, arg: PreImageCheckClause, witness) -> CScript:
        return self._compile(arg.b, witness) +\
               CScript([Op.Sha256]) + self._compile(arg.a, witness) + CScript([Op.Equal])

    @_compile.register
    def _compile_ctv(self, arg: CheckTemplateVerifyClause, witness) -> CScript:
        # While valid to make this a witness variable, this is likely an error
        assert arg.a.value is not None
        assert isinstance(arg.a.value, bytes)
        s = CScript([arg.a.value, Op.CheckTemplateVerify, Op.Drop])
        witness.name(arg.a.value)
        return s

    @_compile.register
    def _compile_after(self, arg: AfterClause, witness) -> CScript:
        # While valid to make this a witness variable, this is likely an error
        assert arg.a.value is not None
        if isinstance(arg.a.value, AbsoluteTimeSpec):
            return CScript([arg.a.value.time, Op.CheckLockTimeVerify, Op.Drop])
        if isinstance(arg.a.value, RelativeTimeSpec):
            return CScript([arg.a.value.time, Op.CheckSequenceVerify, Op.Drop])
        raise ValueError

    @_compile.register
    def _compile_var(self, arg: Variable, witness) -> CScript:
        if arg.value is None:
            # Todo: this is inefficient...
            witness.add(arg.name)
            return CScript()
        else:
            return CScript([arg.value])
