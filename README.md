# 5. Documentação e Orientação

Este documento detalha a solução técnica adotada para o controle de
concorrência no cenário da TechLog e fornece diretrizes para a operação
sustentável do sistema.

## 5.1. Guia Detalhado do Controle de Concorrência

A solução implementada utiliza uma abordagem de **Lock Otimista com
Atualização Atômica** e garantia de **Idempotência**, assegurando que o
estoque nunca fique negativo e que pedidos não sejam duplicados, mesmo
sob alta carga.

------------------------------------------------------------------------

### 1. Mecanismo de Bloqueio (Atomic Row-Level Locking)

Ao invés de bloquear tabelas inteiras, utilizamos o recurso nativo de
transações do banco de dados para serializar atualizações apenas na
linha do produto específico sendo comprado.

A lógica central reside na instrução SQL de atualização condicional:

``` sql
UPDATE produtos
SET estoque = estoque - 1
WHERE id = %s AND estoque > 0;
```

**Como funciona:**\
O comando tenta localizar o registro. O banco de dados adquire um lock
exclusivo (Row-Level Lock) na linha do produto.

**Condição de Guarda:**\
A cláusula `AND estoque > 0` atua como um guardião. Se múltiplas
transações tentarem comprar o último item simultaneamente, o banco as
coloca em fila.\
- A primeira executa e zera o estoque.\
- A segunda, ao ser executada, encontra a condição falsa e não altera
nada (0 linhas afetadas), permitindo que a aplicação trate o erro sem
inconsistências.

------------------------------------------------------------------------

### 2. Garantia de Idempotência (Proteção contra Duplicidade)

Para resolver falhas de comunicação em sistemas distribuídos,
implementamos **chaves de idempotência**.

**Implementação:** Cada tentativa de compra gera um UUID único.

**Restrição:**\
A tabela de pedidos possui uma constraint:

    UNIQUE (chave_idempotencia)

**Resultado:**\
Se um retry ocorrer, o banco rejeita a duplicação e o estoque não é
decrementado duas vezes.

------------------------------------------------------------------------

### 3. Camada de Segurança Final (Database Constraints)

Como defesa em profundidade, o banco possui:

``` sql
estoque INT CHECK (estoque >= 0)
```

Isso garante consistência forte mesmo em caso de falhas da aplicação.

------------------------------------------------------------------------

## 5.2. Recomendações para a Equipe de TI: Monitoramento e Ajuste de Escala

Para garantir estabilidade conforme a demanda cresça, foque em três
pilares:

------------------------------------------------------------------------

### 1. Métricas de Monitoramento (O que observar)

-   **Tempo de Espera por Bloqueio (*Lock Wait Time*):** Configurar alertas para picos no tempo de espera. Valores altos indicam gargalos críticos na concorrência.
-   **Latência de Replicação:** Monitorar o atraso (*lag*) na propagação de dados entre os nós. Atrasos elevados comprometem a consistência dos dados para o utilizador final.
-   **Taxa de *Rollback*:** Acompanhar o volume de transações revertidas. Um aumento repentino sinaliza excesso de conflitos simultâneos pelo mesmo recurso.
------------------------------------------------------------------------

### 2. Ajustes Dinâmicos (Tuning)

-   **Timeouts Agressivos:** Em períodos de alta demanda (como Black Friday), reduzir os *timeouts* das transações para libertar recursos travados mais rapidamente (*fail-fast*), evitando o efeito cascata.
-   **Nível de Isolamento:** Avaliar a redução temporária do isolamento (ex: de *Serializable* para *Read Committed*) em módulos não críticos (como rastreamento de carga) para aumentar a vazão do sistema.

------------------------------------------------------------------------

### 3. Estratégia de Crescimento (Escalabilidade)

-   ***Sharding* (Particionamento):** Caso um nó atinja a saturação, dividir os dados horizontalmente (por região ou ID de cliente) para distribuir a carga de escrita e reduzir bloqueios.
-   **Segregação de Leitura/Escrita (CQRS):** Direcionar relatórios pesados e consultas de histórico exclusivamente para réplicas de leitura, preservando o nó principal para transações críticas.
