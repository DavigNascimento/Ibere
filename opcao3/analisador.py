"""
Analisador léxico e sintático da linguagem PRF.

Gramática completa (é curta de propósito):

    programa  := { definicao }
    definicao := NOME '=' expr
    expr      := 'COMP'   '(' expr ',' '[' expr { ',' expr } ']' ')'
               | 'REC'    '(' expr ',' expr ')'
               | 'MINLIM' '(' expr ',' expr ')'
               | 'MIN'    '(' expr ')'          -- lido, e depois RECUSADO
               | NUMERO
               | NOME                            -- S, Z, Z_n, Pi_n ou definição anterior

Não há `while`, não há `if` como comando, não há atribuição a variável, não
há sequência de comandos e não há chamada de função por nome que ainda não
tenha sido definida. A ausência é o mecanismo de segurança.
"""

import re

from sintaxe import (Comp, Const, Definicao, MinIlim, MinLim, Proj, Rec, Ref,
                     Suc, Zero)


class ErroDeSintaxe(Exception):
    pass


# ---------------------------------------------------------------------------
# 1. Analisador léxico
# ---------------------------------------------------------------------------

TOKEN = re.compile(r"""
      (?P<espaco>[ \t\r]+)
    | (?P<comentario>\#[^\n]*)
    | (?P<nl>\n)
    | (?P<numero>\d+)
    | (?P<nome>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<simbolo>[=(),\[\]])
""", re.VERBOSE)


class Token:
    def __init__(self, tipo, texto, linha):
        self.tipo, self.texto, self.linha = tipo, texto, linha

    def __repr__(self):
        return f"{self.tipo}:{self.texto}"


def tokenizar(fonte):
    tokens, pos, linha = [], 0, 1
    while pos < len(fonte):
        m = TOKEN.match(fonte, pos)
        if m is None:
            raise ErroDeSintaxe(
                f"linha {linha}: caractere inesperado {fonte[pos]!r}")
        pos = m.end()
        tipo = m.lastgroup
        if tipo == "nl":
            linha += 1
        elif tipo in ("espaco", "comentario"):
            pass
        else:
            tokens.append(Token(tipo, m.group(), linha))
    tokens.append(Token("fim", "", linha))
    return tokens


# ---------------------------------------------------------------------------
# 2. Analisador sintático (descida recursiva)
# ---------------------------------------------------------------------------

PROJECAO = re.compile(r"^P(\d+)_(\d+)$")
ZERO = re.compile(r"^Z(?:_(\d+))?$")


class Analisador:
    def __init__(self, fonte):
        self.tokens = tokenizar(fonte)
        self.i = 0

    # -- utilidades ---------------------------------------------------------

    def olhar(self, k=0):
        return self.tokens[min(self.i + k, len(self.tokens) - 1)]

    def avancar(self):
        t = self.tokens[self.i]
        self.i += 1
        return t

    def exigir(self, texto):
        t = self.olhar()
        if t.texto != texto:
            achado = repr(t.texto) if t.texto else "o fim do arquivo"
            raise ErroDeSintaxe(
                f"linha {t.linha}: esperava {texto!r}, encontrei {achado}")
        return self.avancar()

    # -- programa -----------------------------------------------------------

    def programa(self):
        defs = []
        while self.olhar().tipo != "fim":
            defs.append(self.definicao())
        return defs

    def definicao(self):
        t = self.olhar()
        if t.tipo != "nome":
            raise ErroDeSintaxe(
                f"linha {t.linha}: esperava o nome de uma definição, "
                f"encontrei {t.texto!r}")
        nome = self.avancar().texto
        self.exigir("=")
        corpo = self.expr()
        return Definicao(linha=t.linha, nome=nome, corpo=corpo)

    # -- expressões ---------------------------------------------------------

    def expr(self):
        t = self.olhar()

        if t.tipo == "numero":
            self.avancar()
            return Const(linha=t.linha, k=int(t.texto))

        if t.tipo != "nome":
            raise ErroDeSintaxe(
                f"linha {t.linha}: esperava uma expressão, encontrei {t.texto!r}")

        # COMP / REC / MINLIM / MIN são reconhecidos pela abertura de parêntese
        if t.texto == "COMP":
            self.avancar(); self.exigir("(")
            f = self.expr()
            self.exigir(","); self.exigir("[")
            gs = []
            if self.olhar().texto != "]":
                gs.append(self.expr())
                while self.olhar().texto == ",":
                    self.avancar()
                    gs.append(self.expr())
            self.exigir("]"); self.exigir(")")
            return Comp(linha=t.linha, f=f, gs=tuple(gs))

        if t.texto == "REC":
            self.avancar(); self.exigir("(")
            base = self.expr()
            self.exigir(",")
            passo = self.expr()
            self.exigir(")")
            return Rec(linha=t.linha, base=base, passo=passo)

        if t.texto == "MINLIM":
            self.avancar(); self.exigir("(")
            pred = self.expr()
            self.exigir(",")
            limite = self.expr()
            self.exigir(")")
            return MinLim(linha=t.linha, pred=pred, limite=limite)

        if t.texto == "MIN":
            # É aceito pela gramática só para poder ser recusado pelo
            # verificador com uma mensagem explicando o porquê.
            self.avancar(); self.exigir("(")
            pred = self.expr()
            self.exigir(")")
            return MinIlim(linha=t.linha, pred=pred)

        if t.texto in ("WHILE", "LOOP"):
            raise ErroDeSintaxe(
                f"linha {t.linha}: {t.texto!r} não existe nesta linguagem. "
                f"A repetição só é possível por REC (laço de tamanho conhecido) "
                f"ou por MINLIM (busca com teto).")

        # nome simples: S, Z, Z_n, Pi_n ou referência a definição anterior
        self.avancar()
        return self.nome_simples(t)

    def nome_simples(self, t):
        nome = t.texto

        if nome == "S":
            return Suc(linha=t.linha)

        m = ZERO.match(nome)
        if m:
            n = int(m.group(1)) if m.group(1) else 1
            if n < 1:
                raise ErroDeSintaxe(f"linha {t.linha}: Z_0 não existe (aridade >= 1)")
            return Zero(linha=t.linha, n=n)

        m = PROJECAO.match(nome)
        if m:
            i, n = int(m.group(1)), int(m.group(2))
            return Proj(linha=t.linha, i=i, n=n)

        if nome.startswith("P") and "_" in nome and any(c.isdigit() for c in nome):
            raise ErroDeSintaxe(
                f"linha {t.linha}: {nome!r} parece uma projeção malformada. "
                f"A forma correta é P<i>_<n>, por exemplo P2_3.")

        return Ref(linha=t.linha, nome=nome)


def analisar(fonte):
    """Fonte -> lista de Definicao."""
    return Analisador(fonte).programa()


def analisar_expr(fonte):
    """Fonte -> uma única expressão (usado pelo REPL)."""
    a = Analisador(fonte)
    e = a.expr()
    if a.olhar().tipo != "fim":
        raise ErroDeSintaxe(
            f"linha {a.olhar().linha}: sobrou {a.olhar().texto!r} no fim da expressão")
    return e
