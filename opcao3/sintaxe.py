"""
Sintaxe abstrata da linguagem PRF.

Cada nó da árvore é um construtor do cálculo das Funções Recursivas
Primitivas. A lista de nós É a gramática: não existe nó para atribuição,
para salto, para laço `while` nem para chamada recursiva de um nome por
ele mesmo. O que não está aqui não pode ser escrito.

Os dois únicos nós que representam busca são:

  MinLim  — minimização LIMITADA (mu z <= b): sempre para, é aceita;
  MinIlim — minimização ILIMITADA (mu z): existe apenas para que o
            verificador possa recusá-la com uma mensagem clara.
"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class No:
    """Base de todos os nós. `linha` serve para as mensagens de erro."""
    linha: int = field(default=0, compare=False)


# ---------------------------------------------------------------------------
# 1. Funções básicas  (os três tijolos do cálculo)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Zero(No):
    """Z_n(x1,...,xn) = 0.  `Z` sozinho é Z_1."""
    n: int = 1

    def __str__(self):
        return "Z" if self.n == 1 else f"Z_{self.n}"


@dataclass(frozen=True)
class Suc(No):
    """S(x) = x + 1."""

    def __str__(self):
        return "S"


@dataclass(frozen=True)
class Proj(No):
    """P<i>_<n>(x1,...,xn) = xi."""
    i: int = 1
    n: int = 1

    def __str__(self):
        return f"P{self.i}_{self.n}"


# ---------------------------------------------------------------------------
# 2. Açúcar sintático: literais numéricos
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Const(No):
    """
    Literal `k`. É açúcar para COMP(S,[COMP(S,[... Z ...])]) aplicado k vezes,
    ou seja: a função constante de valor k.

    Um literal não tem aridade própria — ele assume a aridade que o contexto
    exigir (constante 0-ária na base de um REC, constante n-ária dentro de
    um COMP). Isso não acrescenta poder algum: constantes já eram definíveis.
    """
    k: int = 0

    def __str__(self):
        return str(self.k)


# ---------------------------------------------------------------------------
# 3. Operadores
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Comp(No):
    """COMP(f,[g1,...,gk])  ->  h(x) = f(g1(x), ..., gk(x))."""
    f: No = None
    gs: Tuple[No, ...] = ()

    def __str__(self):
        return f"COMP({self.f}, [{', '.join(str(g) for g in self.gs)}])"


@dataclass(frozen=True)
class Rec(No):
    """
    REC(f,g)  ->  h(x,0)   = f(x)
                  h(x,y+1) = g(x, y, h(x,y))

    O segundo argumento `y` é o contador da recursão: quando o laço começa
    ele já é um número concreto. São exatamente `y` voltas.
    """
    base: No = None
    passo: No = None

    def __str__(self):
        return f"REC({self.base}, {self.passo})"


@dataclass(frozen=True)
class MinLim(No):
    """
    MINLIM(p, b)  ->  h(x) = mu z <= b(x) [ p(x,z) != 0 ]

    Devolve o menor z <= b(x) que satisfaz o predicado; se nenhum satisfaz,
    devolve b(x)+1. O teto `b` é ele próprio uma expressão da linguagem,
    logo é total: o número de testes é conhecido antes do laço começar.
    """
    pred: No = None
    limite: No = None

    def __str__(self):
        return f"MINLIM({self.pred}, {self.limite})"


@dataclass(frozen=True)
class MinIlim(No):
    """
    MIN(p)  ->  h(x) = mu z [ p(x,z) != 0 ]   -- SEM TETO.

    Existe só para ser recusado. Este é o único operador que transformaria
    a linguagem em Turing-completa, e o verificador o rejeita sempre.
    """
    pred: No = None

    def __str__(self):
        return f"MIN({self.pred})"


# ---------------------------------------------------------------------------
# 4. Referência a uma definição anterior
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Ref(No):
    """
    Nome de uma função já definida ACIMA no arquivo.

    O verificador exige que o nome já exista no ambiente. Como o ambiente só
    cresce depois que a definição termina de ser checada, `F = COMP(S,[F])`
    é impossível: no momento em que o corpo é analisado, `F` ainda não
    existe. É assim que a linguagem proíbe recursão geral por nome.
    """
    nome: str = ""

    def __str__(self):
        return self.nome


# ---------------------------------------------------------------------------
# 5. Definição e programa
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Definicao(No):
    nome: str = ""
    corpo: No = None

    def __str__(self):
        return f"{self.nome} = {self.corpo}"


PALAVRAS_RESERVADAS = {"COMP", "REC", "MINLIM", "MIN", "WHILE", "LOOP", "S", "Z"}
