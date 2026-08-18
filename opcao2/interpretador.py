"""
Avaliador da linguagem PRF.

Cada expressão é compilada para uma função Python (um fecho). A compilação é
literal — cada construtor vira exatamente a sua definição matemática:

    Z_n     -> lambda *x: 0
    S       -> lambda x: x + 1
    Pi_n    -> lambda *x: x[i-1]
    COMP    -> f(g1(x), ..., gk(x))
    REC     -> `for i in range(y)`      <<< laço de tamanho conhecido
    MINLIM  -> `for z in range(b+1)`    <<< laço de tamanho conhecido

Repare que só existem dois laços no arquivo inteiro e ambos são `for` sobre
um `range` calculado ANTES da primeira volta. Não há `while` em lugar nenhum
do avaliador: não existe código que possa girar para sempre.
"""


from sintaxe import (Comp, Const, MinIlim, MinLim, Proj, Rec, Ref, Suc, Zero)
from verificador import ErroDeTotalidade, verificar

# Contador didático: conta aplicações das funções básicas Z, S e P.
PASSOS = {"n": 0}

# Memória de recursão. Calcular h(x,y) por REC produz, no caminho, todos os
# h(x,0..y); guardar essa coluna e reaproveitá-la é sempre correto porque
# TODA função desta linguagem é pura e total — mesmo argumento, mesmo valor,
# sempre, e sem efeito colateral nenhum. (É um luxo que uma linguagem com
# funções parciais não teria: lá, reaproveitar um valor mudaria o que
# termina e o que não termina.)
#
# Sem isso, PRED(y) custa y voltas, e SUB(x,y) — que chama PRED y vezes —
# fica quadrático, o que inviabiliza o Fibonacci. Desligue com
# `interpretador.TABELAS = False` para medir o custo do cálculo puro.
TABELAS = True

# Todas as tabelas vivas, para que uma medição possa começar do zero.
_TABELAS_VIVAS = []


def limpar_tabelas():
    """Esvazia a memória de recursão (usado antes de medir passos)."""
    for t in _TABELAS_VIVAS:
        t.clear()


def zerar_contador():
    PASSOS["n"] = 0


def passos():
    return PASSOS["n"]


class ErroDeExecucao(Exception):
    pass


# ---------------------------------------------------------------------------
# 1. Compilação de expressões
# ---------------------------------------------------------------------------

def compilar(e, ambiente):
    """Expressão -> função Python. `ambiente` mapeia nome -> função já compilada."""

    if isinstance(e, Zero):
        def zero(*_x):
            PASSOS["n"] += 1
            return 0
        return zero

    if isinstance(e, Suc):
        def suc(x):
            PASSOS["n"] += 1
            return x + 1
        return suc

    if isinstance(e, Proj):
        i = e.i - 1

        def proj(*x):
            PASSOS["n"] += 1
            return x[i]
        return proj

    if isinstance(e, Const):
        # açúcar: S aplicado k vezes ao Z, logo custa k+1 passos básicos
        k = e.k

        def const(*_x):
            PASSOS["n"] += k + 1
            return k
        return const

    if isinstance(e, Comp):
        f = compilar(e.f, ambiente)
        gs = tuple(compilar(g, ambiente) for g in e.gs)

        def composta(*x):
            return f(*[g(*x) for g in gs])
        return composta

    if isinstance(e, Rec):
        base = compilar(e.base, ambiente)
        passo = compilar(e.passo, ambiente)
        tabela = {}                     # fatia mais recente: parâmetros -> [h(x,0), h(x,1), ...]
        _TABELAS_VIVAS.append(tabela)

        def recursiva(*args):
            x, y = args[:-1], args[-1]
            if not TABELAS:
                r = base(*x)
                for i in range(y):      # <<< LAÇO LIMITADO: exatamente y voltas
                    r = passo(*x, i, r)
                return r
            # Com memória: o laço já produz h(x,0..y) no caminho, então vale a
            # pena guardar a coluna inteira (ver `TABELAS` no topo do módulo).
            linha = tabela.get(x)
            if linha is None:
                tabela.clear()          # só a fatia de parâmetros mais recente
                linha = [base(*x)]
                tabela[x] = linha
            for i in range(len(linha) - 1, y):   # <<< LAÇO LIMITADO: até y
                linha.append(passo(*x, i, linha[i]))
            return linha[y]
        return recursiva

    if isinstance(e, MinLim):
        pred = compilar(e.pred, ambiente)
        limite = compilar(e.limite, ambiente)

        def busca(*x):
            b = limite(*x)
            for z in range(b + 1):      # <<< LAÇO LIMITADO: no máximo b+1 testes
                if pred(*x, z):
                    return z
            return b + 1                # convenção para "não achou"
        return busca

    if isinstance(e, Ref):
        return ambiente[e.nome]

    if isinstance(e, MinIlim):
        # Inalcançável: o verificador roda antes e recusa. A guarda fica aqui
        # para que nem por engano exista um caminho que compile MIN.
        raise ErroDeTotalidade(
            "MIN (minimização ilimitada) não tem tradução neste avaliador")

    raise ErroDeExecucao(f"nó desconhecido: {e!r}")


# ---------------------------------------------------------------------------
# 2. Funções e programas
# ---------------------------------------------------------------------------

class Funcao:
    """Uma definição já verificada e compilada, pronta para ser aplicada."""

    def __init__(self, nome, aridade, corpo, expr, certificado):
        self.nome = nome
        self.aridade = aridade
        self._corpo = corpo
        self.expr = expr
        self.certificado = certificado

    def __call__(self, *args):
        if len(args) != self.aridade:
            raise ErroDeExecucao(
                f"{self.nome} tem aridade {self.aridade}, recebeu {len(args)} "
                f"argumento(s)")
        for a in args:
            if not isinstance(a, int) or isinstance(a, bool) or a < 0:
                raise ErroDeExecucao(
                    f"{self.nome}: os argumentos são números naturais, recebi {a!r}")
        return self._corpo(*args)

    def com_passos(self, *args):
        """
        Aplica e devolve (resultado, passos básicos gastos), sempre a partir
        de um estado limpo — senão a memória de recursão de uma chamada
        anterior faria a conta parecer mais barata do que é.
        """
        limpar_tabelas()
        zerar_contador()
        r = self(*args)
        return r, passos()

    def __repr__(self):
        return f"<{self.nome}: N^{self.aridade} -> N>"


class Programa:
    """Um arquivo .prf verificado e compilado."""

    def __init__(self, definicoes, base=None):
        """
        `base` é um Programa já verificado sobre o qual estas definições são
        acrescentadas. Serve para o REPL e para testar trechos avulsos sem
        reprocessar a biblioteca — e faz os números de linha dos erros se
        referirem ao trecho, não ao arquivo inteiro.
        """
        novas, self.certificados = verificar(
            definicoes, base.aridades if base else None)
        self.aridades = novas
        self.funcoes = dict(base.funcoes) if base else {}
        self.ordem = list(base.ordem) if base else []
        compilados = dict(base._compilados) if base else {}
        for d, cert in zip(definicoes, self.certificados):
            corpo = compilar(d.corpo, compilados)
            compilados[d.nome] = corpo
            self.funcoes[d.nome] = Funcao(
                d.nome, self.aridades[d.nome], corpo, d.corpo, cert)
            self.ordem.append(d.nome)
        self._compilados = compilados

    def __getitem__(self, nome):
        if nome not in self.funcoes:
            raise ErroDeExecucao(f"{nome!r} não está definido no programa")
        return self.funcoes[nome]

    def __contains__(self, nome):
        return nome in self.funcoes

    def __iter__(self):
        return (self.funcoes[n] for n in self.ordem)

    def __len__(self):
        return len(self.ordem)

    def estender(self, fonte):
        """Devolve um novo Programa = este + as definições de `fonte`."""
        from analisador import analisar
        return Programa(analisar(fonte), base=self)


def carregar(caminho):
    """Lê um arquivo .prf, verifica e compila."""
    from analisador import analisar
    with open(caminho, encoding="utf-8") as f:
        return Programa(analisar(f.read()))


def carregar_texto(fonte):
    from analisador import analisar
    return Programa(analisar(fonte))
