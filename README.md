## 🛒 Simulação de Race Condition (Concorrência) em PostgreSQL

Este projeto é uma Prova de Conceito (PoC) desenvolvida em Python para demonstrar na prática o problema de Race Condition (Condição de Corrida) em sistemas de estoque e como resolvê-lo utilizando transações atômicas no banco de dados.

📋 Sobre o Projeto
O script simula um cenário de "Black Friday" onde:

Existe um produto com estoque limitado (ex: 5 unidades).

Vários clientes (Threads) tentam comprar o produto simultaneamente.

Simula-se um "gap" de processamento entre a leitura do estoque e a gravação.

O objetivo é provar que, sem o tratamento correto de concorrência, o sistema venderá mais produtos do que possui em estoque.

## 🛠️ Tecnologias Utilizadas

Python 3.x

PostgreSQL (via Docker ou Local)

Bibliotecas Python: psycopg2-binary, python-dotenv, uuid

## 🚀 Como Rodar o Projeto

1. Pré-requisitos
   Certifique-se de ter o Python instalado e um banco PostgreSQL rodando.

Se estiver usando Docker (recomendado), suba o banco:

Bash
`docker run --name pg-ecommerce \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=minhasenha123 \
  -e POSTGRES_DB=meu_ecommerce \
  -p 5432:5432 \
  -d postgres`

## 2. Configuração do Ambiente

Clone este repositório ou baixe os arquivos.

Crie um ambiente virtual (opcional, mas recomendado):

Bash
`python -m venv venv`

# Windows

venv\Scripts\activate

# Linux/Mac

source venv/bin/activate
Instale as dependências:

Bash
`pip install psycopg2-binary python-dotenv`

## 3. Configuração de Credenciais (.env)

Crie um arquivo chamado .env na raiz do projeto e configure conforme seu banco de dados.

Exemplo (baseado no Docker acima):

Snippet de código

DB_NAME=meu_ecommerce
DB_USER=admin
DB_PASS=minhasenha123
DB_HOST=localhost
DB_PORT=5432

## 4. Estrutura do Banco (init.sql)

Certifique-se de que o arquivo init.sql está na mesma pasta. O script Python irá lê-lo automaticamente para resetar a tabela a cada teste.

## 5. Executando o Teste

Execute o script principal:

Bash
`app.py`

## 📊 Entendendo os Resultados

O script executará 4 baterias de testes. Ao final de cada uma, ele exibirá um relatório.

# Cenário 1: Vulnerável (Lost Update)

Se o código estiver usando a lógica de "Ler -> Calcular no Python -> Gravar", você verá:

🔴 Race Condition Detectada

Vendas: 8 (para um estoque de 5)

Estoque Final: Inconsistente (pode estar negativo ou errado).

# Cenário 2: Seguro (Atomic Update)

Se o código estiver usando UPDATE ... SET estoque = estoque - 1 WHERE ...:

🟢 Sistema Consistente

Vendas: Exatamente 5.

Tentativas Falhas: 3 usuários receberão "SEM ESTOQUE".

Estoque Final: 0.

## 📂 Estrutura de Arquivos

Plaintext

.
├── .env # Variáveis de ambiente (Senhas) - NÃO COMMITE ISSO
├── .gitignore # Arquivos para o Git ignorar
├── init.sql # Script de criação/reset das tabelas
├── simulacao_v2.py # Código principal da simulação
└── README.md # Documentação

---

# Atividades

# **1\. Análise de Problemas de Concorrência**

## **1.1. Cenários de Conflito e Causas Raiz**

### **Inconsistência de Dados (Race Conditions)**

**Fenômeno Principal:** "Atualização Perdida" (_Lost Update_).

- **O Cenário:** Dois nós distribuídos leem o saldo de um produto (ex: _1 unidade_) simultaneamente. Ambos validam a compra e decrementam o valor, sobrescrevendo a operação um do outro.
- **Causa Raiz:** Falta de **atomicidade** entre a leitura e a escrita, agravada pela latência da rede em sistemas distribuídos. O isolamento inadequado permite que transações concorrentes sobreponham alterações.

### **Bloqueios Prolongados (Deadlocks)**

- **O Cenário:** Transações ficam paradas em estado de espera (`WAIT`) aguardando a liberação de recursos críticos (como tabelas de estoque ou pedidos).
- **Causa Raiz:** Utilização de **Bloqueio Pessimista** (_Pessimistic Locking_) em um ambiente de alta latência. Transações longas retêm os recursos ("trancam" a tabela) enquanto aguardam a comunicação de rede, engarrafando todas as requisições seguintes na fila.

## **1.2. Impacto na Performance do Sistema**

A combinação das falhas acima gera os seguintes impactos operacionais:

1.  **Degradação do Throughput** O sistema processa menos vendas por segundo do que sua capacidade real de hardware, pois o banco de dados gasta recursos gerenciando filas de bloqueio (_Lock Contention_) em vez de efetivar transações.
2.  **Alta Latência** O tempo de resposta para o cliente final aumenta drasticamente, resultando em _timeouts_ de aplicação e abandono de carrinho de compras.
3.  **Esgotamento de Recursos** O acúmulo de transações pendentes consome todo o _pool_ de conexões do banco de dados, levando a erros de **"Serviço Indisponível" (HTTP 503\)** e negação de serviço durante picos de acesso (Black Friday).

# **2\. Proposta de Controle de Concorrência**

Para mitigar os riscos identificados, avaliamos três estratégias clássicas de controle de concorrência.

## **2.1. Análise Comparativa de Técnicas**

### **Bloqueio em Dois Níveis (Two-Phase Locking – 2PL)**

- **Conceito:** Garante serialização estrita dividindo a transação em duas fases: crescimento (adquire todos os locks necessários) e encolhimento (libera os locks).
- **Avaliação:** **Inviável** para a TechLog. Em sistemas distribuídos com alta latência, o 2PL mantém recursos bloqueados por muito tempo, causando _deadlocks_ frequentes e derrubando a performance na Black Friday.

### **Timestamping (Ordenação por Carimbo de Tempo)**

- **Conceito:** Atribui um carimbo de tempo único para cada transação. O sistema aborta qualquer operação que tente alterar um dado "mais novo" com uma transação "mais antiga".
- **Avaliação:** **Essencial como componente**. Sozinho pode ser complexo devido à sincronização de relógios, mas é fundamental quando combinado com controle de versão.

### **Snapshot Isolation (Isolamento de Instantâneo)**

- **Conceito:** A transação opera em uma "versão" (foto) dos dados tirada no início da operação. Leituras nunca bloqueiam escritas, e escritas nunca bloqueiam leituras.
- **Avaliação:** **Ideal**. Permite alta concorrência sem sacrificar a consistência.

## **2.2. Solução Escolhida e Justificativa**

**Técnica Selecionada:** **Snapshot Isolation com Timestamping**.

**Justificativa para o Ambiente TechLog:**

1. **Ordenação Temporal Consistente:** O uso de **Timestamping** atribui marcas temporais precisas (Início e Commit) para cada transação. Isso permite que o banco de dados ordene logicamente os eventos no sistema distribuído, garantindo que cada transação "enxergue" apenas os dados válidos no seu instante de início (Snapshot), sem interferência de modificações futuras.
2. **Detecção de Conflitos (First-Committer-Wins):** A combinação utiliza o timestamp para aplicar a regra do "Primeiro a Comitar Vence". Se duas transações concorrentes tentam modificar o mesmo dado (baseadas no mesmo snapshot inicial), o sistema compara os timestamps de commit. A segunda transação detecta que o dado já possui um timestamp mais recente do que o seu snapshot de leitura e falha automaticamente, prevenindo a "Atualização Perdida" sem necessidade de bloqueios prévios.
3. **Performance de Leitura na Black Friday:** Como as leituras são baseadas em timestamps passados (snapshots), elas nunca são bloqueadas por locks de escrita. Isso garante que a navegação pelo catálogo e a consulta de preços permaneçam rápidas, mesmo enquanto o sistema processa milhares de atualizações de estoque.

---

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
