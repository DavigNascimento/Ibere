# Tema: O Limite do laço `for` vs. `while`: Simulando a Fronteira entre FRP e FRG

- **Objetivo:** Fazer o aluno vivenciar na prática a diferença de poder expressivo entre Funções Recursivas Primitivas e Gerais, além de entender a explosão de complexidade da Função de Ackermann.

- **O que o aluno deve desenvolver:**

  1. **Módulo FRP (Laços finitos/limitados):**
     - Implementar as funções básicas ($Z$, $S$, $P_i^n$) e os operadores de Composição e Recursão Primitiva.
     - Construir Operações Aritméticas (Adição, Multiplicação, Potenciação e Fatorial) estritamente como FRP.
     - Implementar o algoritmo de Minimização Limitada $\mu y \leq b$ e aplicar no cálculo da Raiz Quadrada Piso ($\lfloor \sqrt{x} \rfloor$).

  2. **Módulo FRG (Laços indefinidos):**
     - Implementar a Função de Ackermann $A(m, n)$.
     - Implementar uma busca por Minimização Não-Limitada ($\mu y$).

  3. **Módulo de Benchmark / Monitoramento:**
     - Criar um script que meça o tempo de execução e o consumo/profundidade da pilha de chamadas (call stack) para $A(m, n)$ à medida que $m$ e $n$ crescem.

- **O que apresentar:**
  - Apresentar o gráfico de consumo de memória da Função de Ackermann demonstrando o *stack overflow* (estouro de pilha) mesmo para entradas minúsculas (ex: $A(4, 2)$).
  - Explicar por que a minimização limitada garante que o código nunca entre em loop infinito, provando a correspondência com o laço `for`.