# Mini-interpretador da linguagem PRF

Uma linguagem de programação em que **é impossível escrever um laço infinito**,
e um interpretador em Python que a executa. A garantia não vem de análise
esperta: vem de o construtor perigoso simplesmente não existir na gramática.

Toda função escrita nesta linguagem é **total por construção** — para com
resposta para qualquer entrada. Isso é verificado estaticamente, antes de
qualquer avaliação.

## Como rodar

```bash
python3 main.py          # relatório completo (~10 s, sem dependências)
python3 main.py --repl   # modo interativo
python3 testes.py        # confere tudo contra os operadores do Python
```

Não usa nenhuma biblioteca externa.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `sintaxe.py` | Árvore sintática: um nó por construtor do cálculo |
| `analisador.py` | Analisador léxico e sintático (descida recursiva) |
| `verificador.py` | Verificação estática: aridades + totalidade + aciclicidade |
| `interpretador.py` | Compilação para fechos Python e avaliação |
| `biblioteca.prf` | 33 definições **escritas na linguagem**, incluindo os 3 problemas |
| `main.py` | Roda tudo e imprime o relatório |
| `testes.py` | Conferência automática (semântica e recusas) |

---

## 1. A linguagem

### Sintaxe

```
ADD = REC(P1_1, COMP(S, [P3_3]))
```

A gramática inteira:

```
programa  := { definicao }
definicao := NOME '=' expr
expr      := 'COMP'   '(' expr ',' '[' expr { ',' expr } ']' ')'
           | 'REC'    '(' expr ',' expr ')'
           | 'MINLIM' '(' expr ',' expr ')'
           | 'MIN'    '(' expr ')'          -- lido só para ser RECUSADO
           | NUMERO                          -- literal (constante)
           | NOME                            -- S | Z | Z_n | Pi_n | definição anterior
```

| Construtor | Significado |
|---|---|
| `Z`, `Z_n` | $Z(x_1,\dots,x_n) = 0$ |
| `S` | $S(x) = x+1$ |
| `Pi_n` | $P_i^n(x_1,\dots,x_n) = x_i$ |
| `k` | literal: açúcar para `S` aplicado $k$ vezes ao `Z` |
| `COMP(f,[g1..gk])` | $h(\vec x) = f(g_1(\vec x),\dots,g_k(\vec x))$ |
| `REC(f,g)` | $h(\vec x,0)=f(\vec x)$, $h(\vec x,y{+}1)=g(\vec x,y,h(\vec x,y))$ |
| `MINLIM(p,b)` | $h(\vec x) = \mu z \le b(\vec x)\,[\,p(\vec x,z)\ne 0\,]$ |

Comentários começam com `#`. Um literal não tem aridade própria: assume a que o
contexto exigir (`COMP(MULT,[P1_1, 2])` dobra um número; `REC(1, ...)` usa `1`
como caso base 0-ário). Isso é conveniência, não poder novo — constantes já
eram definíveis com `COMP(S,[...COMP(S,[Z])...])`.

### O que **não** existe

Atribuição a variável, sequência de comandos, `while`, `loop`, `if` como desvio
de fluxo, chamada a um nome ainda não definido, e minimização ilimitada. Cada
uma dessas ausências é uma decisão, e cada uma está justificada na seção 5.

### Exemplo: a biblioteca

```prf
ADD  = REC(P1_1, COMP(S, [P3_3]))            # ADD(x,y+1) = S(ADD(x,y))
MULT = REC(Z, COMP(ADD, [P3_3, P1_3]))       # MULT(x,y+1) = ADD(MULT(x,y), x)
PRED = REC(0, P1_2)                          # PRED(y+1) = y
SUB  = REC(P1_1, COMP(PRED, [P3_3]))         # subtração truncada
SG   = REC(0, 1)                             # SG(x) = 1 se x != 0
LEQ  = COMP(NSG, [SUB])                      # x <= y  <=>  x - y == 0
```

O condicional também é uma função, não um desvio:

```prf
SE = COMP(ADD, [COMP(MULT, [COMP(SG,  [P1_3]), P2_3]),
                COMP(MULT, [COMP(NSG, [P1_3]), P3_3])])
```

`SE(c,a,b) = c·a + (1−c)·b`. Os **dois ramos são sempre avaliados** — o que
seria um desperdício numa linguagem comum, e aqui é inofensivo: nenhum ramo
pode travar, porque nada nesta linguagem trava.

---

## 2. O verificador estático

Roda antes de qualquer avaliação (`verificador.py`) e faz três coisas.

### (a) Tipos = aridades

O único tipo é $\mathbb{N}^n \to \mathbb{N}$, então "checar tipo" é checar
aridade. As regras:

$$\frac{}{\vdash Z_n : \mathbb{N}^n \to \mathbb{N}} \qquad
\frac{}{\vdash S : \mathbb{N}^1 \to \mathbb{N}} \qquad
\frac{1 \le i \le n}{\vdash P_i^n : \mathbb{N}^n \to \mathbb{N}}$$

$$\frac{\vdash f : \mathbb{N}^k \to \mathbb{N} \qquad \vdash g_j : \mathbb{N}^n \to \mathbb{N}}
       {\vdash \mathrm{COMP}(f,[g_1..g_k]) : \mathbb{N}^n \to \mathbb{N}} \qquad
\frac{\vdash f : \mathbb{N}^n \to \mathbb{N} \qquad \vdash g : \mathbb{N}^{n+2} \to \mathbb{N}}
     {\vdash \mathrm{REC}(f,g) : \mathbb{N}^{n+1} \to \mathbb{N}}$$

$$\frac{\vdash p : \mathbb{N}^{n+1} \to \mathbb{N} \qquad \vdash b : \mathbb{N}^n \to \mathbb{N}}
       {\vdash \mathrm{MINLIM}(p,b) : \mathbb{N}^n \to \mathbb{N}}$$

Exemplos de recusa (mensagens reais do programa):

```
X = COMP(ADD, [P1_1])
  -> ErroDeAridade: ADD tem aridade 2, mas o contexto exige aridade 1

X = COMP(ADD, [P1_1, P1_2])
  -> ErroDeAridade: os argumentos de COMP têm aridades diferentes [1, 2]

X = P4_3
  -> ErroDeAridade: P4_3 projeta o argumento 4 de uma lista de 3 argumentos

X = REC(P1_1, COMP(S,[P1_2]))
  -> ErroDeAridade: P1_1 tem aridade 1, mas o contexto exige aridade 0
     (neste REC os parâmetros são n = 0: a base precisa de aridade 0 e o passo, de 2)
```

### (b) Totalidade

Percorre a árvore e confere que **todo nó pertence ao fecho de $\{Z, S, P_i^n\}$
sob COMP, REC e MINLIM**. Encontrando `MIN`, recusa:

```
BUSCA = MIN(COMP(EQ, [COMP(MULT,[P2_2,P2_2]), P1_2]))
  -> ErroDeTotalidade: MIN (minimização ilimitada, mu z sem teto) é proibida.
     mu z [ p(x,z) = 0 ] pode nunca encontrar z, e aí a função fica indefinida
     naquele ponto — deixa de ser total. Use MINLIM(p, b), que testa z = 0..b(x)
     e devolve b(x)+1 se não achar.
```

`WHILE` e `LOOP` nem chegam ao verificador — morrem no analisador sintático.

### (c) Aciclicidade

Um nome só enxerga definições **anteriores**. O ambiente só recebe `F` depois
que o corpo de `F` foi checado, então auto-referência e referência mútua são
mecanicamente impossíveis:

```
LOOPY = COMP(S, [LOOPY])
  -> ErroDeAridade: 'LOOPY' não foi definido antes deste ponto.

PAR   = COMP(NSG, [IMPAR])
IMPAR = COMP(NSG, [PAR])
  -> ErroDeAridade: 'IMPAR' não foi definido antes deste ponto.
```

Redefinir um nome também é recusado, senão daria para fabricar ciclos.

### O certificado

Passando nas três, o verificador emite para cada definição um certificado com
tipo, profundidade da árvore, construtores usados e dependências. É o que a
seção 1 do relatório imprime:

```
  função       tipo         prof  construtores usados          busca
  ADD          N^2 -> N        3  S P COMP REC                 -
  QUOC         N^2 -> N        5  S P COMP MINLIM nome         MINLIM
  FIB          N^1 -> N        3  P COMP nome                  -
```

---

## 3. O avaliador

Cada expressão é compilada para um fecho Python. A tradução é literal:

```python
Z_n     ->  lambda *x: 0
S       ->  lambda x: x + 1
Pi_n    ->  lambda *x: x[i-1]
COMP    ->  f(g1(x), ..., gk(x))
REC     ->  for i in range(y)      # laço de tamanho conhecido
MINLIM  ->  for z in range(b + 1)  # laço de tamanho conhecido
```

**O arquivo `interpretador.py` não contém nenhum `while`.** Só existem dois
laços, ambos `for` sobre um `range` calculado **antes** da primeira volta:

```python
def recursiva(*args):
    x, y = args[:-1], args[-1]
    r = base(*x)
    for i in range(y):          # exatamente y voltas; y já é um número
        r = passo(*x, i, r)
    return r

def busca(*x):
    b = limite(*x)              # o teto é ele próprio uma função total
    for z in range(b + 1):      # no máximo b+1 testes
        if pred(*x, z):
            return z
    return b + 1                # convenção para "não achou"
```

### Memória de recursão

Calcular $h(\vec x,y)$ por REC produz, no caminho, todos os $h(\vec x,0..y)$.
O avaliador guarda essa coluna e a reaproveita. **Isso só é seguro porque toda
função da linguagem é pura e total** — mesmo argumento, mesmo valor, sempre,
sem efeito colateral e sem "às vezes não termina". Numa linguagem com funções
parciais a troca mudaria o que termina e o que não termina.

Sem isso `PRED(y)` custaria $y$ voltas e `SUB(x,y)` — que chama `PRED` $y$
vezes — ficaria quadrático, o que inviabilizaria o Fibonacci:

| chamada | com memória | sem memória |
|---|---:|---:|
| `SUB(300, 300)` | 602 | 45.751 |
| `RESTO(200, 7)` | 8.367 | 440.985 |
| `FIB(7)` | 46.925 | 2.308.715 |

Desligue com `interpretador.TABELAS = False`. Os resultados não mudam — só o
preço. `testes.py` confere exatamente isso.

---

## 4. Os três problemas

### Problema A — divisão inteira

```prf
QUOC  = MINLIM(COMP(LT, [P1_3, COMP(MULT, [COMP(S, [P3_3]), P2_3])]), P1_2)
DIV   = COMP(MULT, [COMP(SG, [P2_2]), QUOC])
RESTO = COMP(SUB, [P1_2, COMP(MULT, [P2_2, DIV])])
```

Isto é $\mathrm{QUOC}(x,y) = \mu z \le x\,[\,x < (z{+}1)\cdot y\,]$. O teto é
`P1_2`, o próprio $x$: o quociente de $x$ por um $y \ge 1$ nunca passa de $x$,
então a resposta certamente cabe na faixa — e são no máximo $x+1$ testes,
decididos antes da primeira volta.

**Divisão por zero:** em vez de "indefinido", que quebraria a totalidade, a
linguagem devolve $\mathrm{DIV}(x,0) = 0$ e $\mathrm{RESTO}(x,0) = x$. Uma
função total não tem o direito de não responder.

```
    x |  y | DIV | RESTO | conferência x = y*q + r
    7 |  2 |   3 |     1 | 2*3 + 1 = 7
  100 |  7 |  14 |     2 | 7*14 + 2 = 100
  144 | 12 |  12 |     0 | 12*12 + 0 = 144
```

372 pares conferidos contra `//` e `%` do Python, zero divergências.

### Problema B — teste de primalidade

```prf
DIVISOR  = COMP(MULT, [COMP(SG,[P1_2]), COMP(NSG, [COMP(RESTO,[P2_2, P1_2])])])
CONTADIV = REC(Z, COMP(ADD, [P3_3, COMP(DIVISOR,[COMP(S,[P2_3]), P1_3])]))
NUMDIV   = COMP(CONTADIV, [P1_1, P1_1])
PRIMO    = COMP(EQ, [NUMDIV, 2])
```

`CONTADIV(n,k)` conta por recursão em $k$ os divisores de $n$ em $1..k$, e
`NUMDIV(n) = CONTADIV(n,n)`. Primo é ter exatamente 2 divisores — os casos
$n=0$ e $n=1$ saem certos sem nenhum tratamento especial.

```
Primos até 59: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]
PRIMO(97) = 1  em 147.769 aplicações de Z, S e P.
```

Repare que o custo é $O(n^2 \log n)$ e não há como fazer melhor com um "sai
mais cedo": não existe `break`. O laço vai até o fim, sempre — é justamente
isso que torna o custo previsível.

### Problema C — Fibonacci

$F(n{+}2) = F(n{+}1) + F(n)$ precisa de **dois** valores anteriores, mas `REC`
entrega **um** só (o $h(\vec x,y)$ do passo). E não dá para "guardar uma
variável a mais", porque não existem variáveis. A saída é a clássica: carregar
o par $(F(k), F(k{+}1))$ codificado num único número, na base $B$.

$$z_k = F(k)\cdot B + F(k{+}1), \qquad
  z_{k+1} = b\cdot B + (a{+}b), \quad a = \mathrm{DIV}(z,B),\; b = \mathrm{RESTO}(z,B)$$

```prf
EXPO = COMP(DIV, [COMP(ADD, [COMP(MULT, [7, P1_1]), 9]), 10])
BASE = COMP(S, [COMP(POT, [2, EXPO])])
FIBH = REC(1, COMP(ADD, [COMP(MULT, [COMP(RESTO, [P3_3, P1_3]), P1_3]),
                         COMP(ADD,  [COMP(DIV,   [P3_3, P1_3]),
                                     COMP(RESTO, [P3_3, P1_3])])]))
FIB  = COMP(DIV, [COMP(FIBH, [BASE, P1_1]), BASE])
```

É por isso que o Fibonacci **depende** do problema A: sem divisão inteira não
se desempacota o par. E o teto $B$ tem que ser calculável de antemão: serve
qualquer $B > F(n{+}1)$, e $2^n{+}1$ bastaria, mas o custo é proporcional a
$B$, então vale apertar. Como $F(n{+}1) \sim \varphi^n$ com $\varphi = 1{,}6180$
e $2^{0,7} = 1{,}6245 > \varphi$, usamos

$$B(n) = 2^{\lceil 0,7n \rceil} + 1, \qquad \lceil 0,7n \rceil = \lfloor (7n+9)/10 \rfloor$$

que é ~8× menor que $2^n$ em $n=10$ e continua sendo limite válido.

```
    n | FIB(n) |  base B | passos básicos |  tempo
    8 |     21 |      65 |        171.716 |   0.04s
   10 |     55 |     129 |      1.543.521 |   0.34s
   12 |    144 |     513 |     34.645.498 |   7.15s
```

O tempo multiplicando-se por ~4 a cada $n$ **não é defeito do interpretador**:
é o preço de ter só o sucessor como operação primitiva. `MULT(a,b)` custa $a
\cdot b$ passos porque soma $b$ vezes; `DIV` custa uma busca. Totalidade sai de
graça; eficiência, não.

---

## 5. Por que a sintaxe impede turing-completude e laços infinitos

### (a) O argumento estrutural — indução sobre a árvore

Toda expressão é folha (`Z`, `S`, `Pi_n`, literal) ou um dos três operadores.
Por indução estrutural:

| caso | por quê para |
|---|---|
| `Z`, `S`, `Pi_n`, literal | param em número fixo de passos |
| `COMP` | $f$ e $g_j$ param (h.i.); soma finita de trabalho finito |
| `REC` | faz exatamente $y$ chamadas de $g$; $y$ **já é um número** quando o laço começa, e o laço não pode alterá-lo |
| `MINLIM` | faz no máximo $b(\vec x)+1$ testes; $b$ é total (h.i.), logo $b(\vec x)$ é um número antes do laço começar |

**Não há caso indutivo faltando porque não há mais construtores.** É a lista
de nós de `sintaxe.py`, e ela é fechada. Logo todo programa da linguagem para.

### (b) O que foi retirado, e por que essas eram as peças perigosas

1. **$\mu$ ilimitado.** Teorema de Kleene: FRP + minimização ilimitada =
   funções recursivas gerais = turing-completo. Essa é *a* peça, e é
   exatamente o que `MIN` seria. Existe na gramática só para ser recusado com
   uma mensagem que explica o motivo.
2. **Auto-referência.** Sem operador de ponto fixo e sem nome visível dentro
   do próprio corpo, não há recursão geral. A recursão que sobra é a do `REC`,
   que decresce um contador concreto.
3. **`while` / `loop`.** Não entram nem no analisador sintático.
4. **Condicional como função, não como desvio.** Os dois ramos são sempre
   avaliados, então não existe "ramo que não termina".

### (c) O argumento de diagonalização — por que a perda é inevitável

Toda linguagem **total** cujos programas são enumeráveis deixa funções
computáveis de fora. Os programas são cadeias finitas sobre alfabeto finito,
então enumere-os: $f_0, f_1, f_2, \dots$ Defina

$$d(n) = f_n(n) + 1$$

$d$ é computável (basta simular $f_n$, que sempre para) e total, mas difere de
todo $f_n$ no ponto $n$. Logo $d$ não está na linguagem.

Não é falha de projeto: é o **preço de decidir a parada de graça**. Corolário
prático: um interpretador universal de PRF não é escrevível em PRF — se fosse,
$d$ também seria. É o que separa esta linguagem de um Python ou de uma máquina
de Turing, onde o interpretador universal existe e a parada é indecidível.

### (d) O exemplo concreto — Ackermann

$$A(0,n) = n+1, \quad A(m{+}1,0) = A(m,1), \quad A(m{+}1,n{+}1) = A(m, A(m{+}1,n))$$

Total e computável, mas cresce mais rápido que qualquer FRP: para todo programa
PRF $f$ de aridade 1 existe $m$ com $A(m,n) > f(n)$ para $n$ grande. Tentar
escrevê-la aqui esbarra na estrutura: a recursão de Ackermann é **aninhada**,
sobre dois argumentos ao mesmo tempo, e `REC` só recorre no **último**, com os
demais fixos como parâmetros. Não existe onde encaixar $A(m{+}1,n)$ dentro de
um `REC` — e, pelo item (a), se existisse, a prova de totalidade estaria errada.

> Este é exatamente o outro lado da opção 1 (`../opcao1`), onde Ackermann é
> implementada em FRG com `while` e estoura a pilha com entradas de um dígito.
> Aqui ela não estoura nada: ela não é escrevível.

### (e) A troca, em uma linha

A linguagem não computa tudo o que é computável, mas sobre ela o problema da
parada é **decidível** — e a resposta é sempre "sim".

---

## 6. O preço, medido

Passos básicos = aplicações de `Z`, `S` e `P` (o relatório imprime a tabela):

```
    ADD(30, 40) = 70                    81 passos
    MULT(12, 12) = 144                 325 passos
    POT(2, 10) = 1024                4.184 passos
    FAT(7) = 5040                   14.470 passos
    DIV(100, 7) = 14                 2.507 passos
    PRIMO(91) = 0                  130.634 passos
    FIB(12) = 144               34.645.498 passos
```

Cada um desses números é finito, e o verificador já sabia disso antes de rodar.

## 7. Notas

- `MINLIM` é conveniência, não poder novo: minimização limitada é definível a
  partir de `COMP` e `REC`. Está no núcleo porque torna `DIV` e `RAIZ`
  legíveis, e porque é o contraste didático direto com `MIN`.
- A convenção de `MINLIM` quando nada satisfaz o predicado é devolver
  $b(\vec x)+1$. Alguma convenção é obrigatória: "indefinido" não é opção numa
  linguagem total.
- O enunciado sugere `ADD = REC(P1_1, COMP(S, [P2_3]))`. Esse programa **passa**
  no verificador — é total e as aridades fecham —, mas `P2_3` projeta o contador
  $y$ em vez do resultado parcial $r$, então define outra função
  ($h(x,0)=x$, $h(x,y)=y$ para $y\ge1$). A soma é `P3_3`. O verificador garante
  totalidade, não intenção; o relatório mostra as duas lado a lado.
