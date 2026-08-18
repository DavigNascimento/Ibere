"""
Verificação estática: aridades + certificado de totalidade.

O verificador roda ANTES de qualquer avaliação e faz três coisas:

  1. TIPOS. O único tipo da linguagem é `N^n -> N`, ou seja, o "tipo" de uma
     expressão é a sua aridade n. Toda composição, toda recursão e toda
     minimização limitada tem uma regra de aridade; quem não fecha é
     recusado antes de rodar.

  2. TOTALIDADE. Percorre a árvore e confere que todo nó pertence ao fecho
     de {Z, S, P} pelos operadores COMP, REC e MINLIM. Se encontrar um MIN
     (minimização ilimitada), recusa o programa.

  3. ACICLICIDADE. Um nome só pode referenciar definições ANTERIORES. Sem
     auto-referência e sem referência mútua não há como escrever recursão
     geral disfarçada de chamada de função.

Se as três passam, o programa é total por construção: a prova é a própria
derivação, por indução estrutural sobre a árvore (ver `certificado`).
"""

from sintaxe import (Comp, Const, MinIlim, MinLim, Proj, Rec, Ref, Suc,
                     Zero)


class ErroDeAridade(Exception):
    """Regra de tipo violada: as aridades não fecham."""


class ErroDeTotalidade(Exception):
    """Construção que poderia não terminar. Recusada por princípio."""


# ---------------------------------------------------------------------------
# 1. Regras de aridade
# ---------------------------------------------------------------------------

def _exigir(obtida, exigida, e, quem):
    if exigida is not None and obtida != exigida:
        raise ErroDeAridade(
            f"linha {e.linha}: {quem} tem aridade {obtida}, "
            f"mas o contexto exige aridade {exigida}  ->  {e}")
    return obtida


def aridade(e, ambiente, exigida=None):
    """
    Devolve a aridade de `e`, conferindo as regras. `exigida` é a aridade que
    o contexto pede (None = ainda não decidida).

    Regras, na notação de sequente:

        ------------------- Z_n            ------------------- S
          |- Z_n : N^n -> N                  |- S : N^1 -> N

        1 <= i <= n
        ------------------- P
          |- Pi_n : N^n -> N

          |- f : N^k -> N     |- gj : N^n -> N   (j = 1..k)
        ------------------------------------------------------ COMP
          |- COMP(f,[g1..gk]) : N^n -> N

          |- f : N^n -> N     |- g : N^(n+2) -> N
        ------------------------------------------ REC
          |- REC(f,g) : N^(n+1) -> N

          |- p : N^(n+1) -> N     |- b : N^n -> N
        ------------------------------------------ MINLIM
          |- MINLIM(p,b) : N^n -> N
    """
    # -- literal: assume a aridade que o contexto pedir -------------------
    if isinstance(e, Const):
        if e.k < 0:
            raise ErroDeAridade(f"linha {e.linha}: literal negativo {e.k}")
        return 0 if exigida is None else exigida

    if isinstance(e, Zero):
        return _exigir(e.n, exigida, e, f"Z_{e.n}")

    if isinstance(e, Suc):
        return _exigir(1, exigida, e, "S")

    if isinstance(e, Proj):
        if e.n < 1:
            raise ErroDeAridade(f"linha {e.linha}: P{e.i}_{e.n} tem aridade {e.n} < 1")
        if not 1 <= e.i <= e.n:
            raise ErroDeAridade(
                f"linha {e.linha}: P{e.i}_{e.n} projeta o argumento {e.i} de uma "
                f"lista de {e.n} argumentos — índice fora da faixa 1..{e.n}")
        return _exigir(e.n, exigida, e, f"P{e.i}_{e.n}")

    if isinstance(e, Ref):
        if e.nome not in ambiente:
            raise ErroDeAridade(
                f"linha {e.linha}: {e.nome!r} não foi definido antes deste ponto. "
                f"Nesta linguagem um nome só enxerga definições anteriores — é "
                f"isso que impede recursão geral por auto-referência.")
        return _exigir(ambiente[e.nome], exigida, e, e.nome)

    if isinstance(e, Comp):
        k = len(e.gs)
        if k == 0:
            raise ErroDeAridade(
                f"linha {e.linha}: COMP com lista de argumentos vazia")
        aridade(e.f, ambiente, k)          # f precisa receber exatamente k valores
        concretos = [g for g in e.gs if not isinstance(g, Const)]
        if concretos:
            ars = [aridade(g, ambiente) for g in concretos]
            if len(set(ars)) > 1:
                raise ErroDeAridade(
                    f"linha {e.linha}: os argumentos de COMP têm aridades "
                    f"diferentes {sorted(set(ars))} — todos precisam receber os "
                    f"mesmos x1..xn  ->  {e}")
            n = ars[0]
        else:
            n = 0 if exigida is None else exigida
        _exigir(n, exigida, e, "COMP")
        for g in e.gs:
            aridade(g, ambiente, n)
        return n

    if isinstance(e, Rec):
        # n vem do passo (aridade n+2); se o passo for literal, vem da base.
        if not isinstance(e.passo, Const):
            ag = aridade(e.passo, ambiente)
            if ag < 2:
                raise ErroDeAridade(
                    f"linha {e.linha}: o passo de REC recebe (x1..xn, y, r), logo "
                    f"precisa de aridade n+2 >= 2, mas tem {ag}  ->  {e}")
            n = ag - 2
        elif not isinstance(e.base, Const):
            n = aridade(e.base, ambiente)
        else:
            n = 0                           # REC(k1, k2): recursão sem parâmetros
        try:
            aridade(e.base, ambiente, n)
            aridade(e.passo, ambiente, n + 2)
        except ErroDeAridade as erro:
            raise ErroDeAridade(
                f"{erro}\n        (neste REC os parâmetros são n = {n}: a base "
                f"precisa de aridade {n} e o passo, de {n + 2})") from None
        return _exigir(n + 1, exigida, e, "REC")

    if isinstance(e, MinLim):
        if not isinstance(e.limite, Const):
            n = aridade(e.limite, ambiente)
        elif not isinstance(e.pred, Const):
            ap = aridade(e.pred, ambiente)
            if ap < 1:
                raise ErroDeAridade(
                    f"linha {e.linha}: o predicado de MINLIM recebe (x1..xn, z), "
                    f"logo precisa de aridade n+1 >= 1")
            n = ap - 1
        else:
            n = 0 if exigida is None else exigida
        try:
            aridade(e.pred, ambiente, n + 1)
            aridade(e.limite, ambiente, n)
        except ErroDeAridade as erro:
            raise ErroDeAridade(
                f"{erro}\n        (neste MINLIM os parâmetros são n = {n}: o "
                f"predicado precisa de aridade {n + 1} e o teto, de {n})") from None
        return _exigir(n, exigida, e, "MINLIM")

    if isinstance(e, MinIlim):
        raise ErroDeTotalidade(
            f"linha {e.linha}: MIN (minimização ilimitada, mu z sem teto) é "
            f"proibida.\n"
            f"        mu z [ p(x,z) = 0 ] pode nunca encontrar z, e aí a função "
            f"fica indefinida\n"
            f"        naquele ponto — deixa de ser total. Use "
            f"MINLIM(p, b), que testa z = 0..b(x)\n"
            f"        e devolve b(x)+1 se não achar. Sem esse operador não há "
            f"laço infinito possível.")

    raise ErroDeAridade(f"nó desconhecido: {e!r}")


# ---------------------------------------------------------------------------
# 2. Certificado de totalidade
# ---------------------------------------------------------------------------

def operadores_usados(e, acc=None):
    """Conjunto de construtores que aparecem na árvore (sem entrar em Ref)."""
    acc = set() if acc is None else acc
    acc.add(type(e).__name__)
    if isinstance(e, Comp):
        operadores_usados(e.f, acc)
        for g in e.gs:
            operadores_usados(g, acc)
    elif isinstance(e, Rec):
        operadores_usados(e.base, acc)
        operadores_usados(e.passo, acc)
    elif isinstance(e, MinLim):
        operadores_usados(e.pred, acc)
        operadores_usados(e.limite, acc)
    elif isinstance(e, MinIlim):
        operadores_usados(e.pred, acc)
    return acc


def profundidade(e):
    if isinstance(e, Comp):
        return 1 + max([profundidade(e.f)] + [profundidade(g) for g in e.gs])
    if isinstance(e, Rec):
        return 1 + max(profundidade(e.base), profundidade(e.passo))
    if isinstance(e, MinLim):
        return 1 + max(profundidade(e.pred), profundidade(e.limite))
    return 1


def dependencias(e, acc=None):
    acc = set() if acc is None else acc
    if isinstance(e, Ref):
        acc.add(e.nome)
    elif isinstance(e, Comp):
        dependencias(e.f, acc)
        for g in e.gs:
            dependencias(g, acc)
    elif isinstance(e, Rec):
        dependencias(e.base, acc)
        dependencias(e.passo, acc)
    elif isinstance(e, MinLim):
        dependencias(e.pred, acc)
        dependencias(e.limite, acc)
    return acc


NOME_LEGIVEL = {
    "Zero": "Z", "Suc": "S", "Proj": "P", "Const": "literal",
    "Comp": "COMP", "Rec": "REC", "MinLim": "MINLIM", "Ref": "nome",
}


class Certificado:
    """O que o verificador garante sobre uma definição."""

    def __init__(self, nome, expr, aridade_, operadores, profundidade_, deps):
        self.nome = nome
        self.expr = expr
        self.aridade = aridade_
        self.operadores = operadores
        self.profundidade = profundidade_
        self.dependencias = deps

    @property
    def usa_busca_limitada(self):
        return "MinLim" in self.operadores

    def resumo_operadores(self):
        ordem = ["Zero", "Suc", "Proj", "Const", "Comp", "Rec", "MinLim", "Ref"]
        return " ".join(NOME_LEGIVEL[o] for o in ordem if o in self.operadores)


def verificar(definicoes, ambiente_inicial=None):
    """
    Confere o programa inteiro, na ordem. Devolve (ambiente, certificados).
    Levanta ErroDeAridade ou ErroDeTotalidade na primeira definição inválida.

    `ambiente_inicial` permite verificar um trecho novo em cima de um
    programa já verificado (é o que o REPL faz).
    """
    ambiente = dict(ambiente_inicial or {})
    certificados = []
    for d in definicoes:
        if d.nome in ambiente:
            raise ErroDeAridade(
                f"linha {d.linha}: {d.nome!r} já foi definido. Redefinir um nome "
                f"permitiria fabricar ciclos entre definições.")
        # O nome AINDA NÃO está no ambiente aqui: auto-referência é impossível.
        n = aridade(d.corpo, ambiente)
        ambiente[d.nome] = n
        certificados.append(Certificado(
            d.nome, d.corpo, n,
            operadores_usados(d.corpo),
            profundidade(d.corpo),
            dependencias(d.corpo),
        ))
    return ambiente, certificados
