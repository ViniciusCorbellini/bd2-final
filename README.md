# 🛒 Simulação de Race Condition (Concorrência) em PostgreSQL

Este projeto é uma Prova de Conceito (PoC) em **Python** para demonstrar, na prática, o problema de **Race Condition** em sistemas de estoque e como resolvê-lo utilizando **transações atômicas** e **controle de concorrência no banco de dados**.

O cenário é inspirado em uma situação de **Black Friday** em um e-commerce (TechLog), com múltiplos clientes tentando comprar o mesmo produto simultaneamente.

---

## 1. Sobre o Projeto

O script simula um cenário onde:

- Existe um produto com estoque limitado (ex.: **5 unidades**).
- Vários clientes (threads) tentam comprar o mesmo produto ao mesmo tempo.
- Há um "gap" de processamento entre a leitura do estoque e a gravação.
- O objetivo é mostrar que, **sem controle de concorrência adequado**, o sistema pode vender **mais itens do que há em estoque**.

A partir desse problema, o projeto também discute e documenta:
- Técnicas de controle de concorrência em bancos de dados.
- Impactos em performance, consistência e escalabilidade em ambientes distribuídos.

---

## 2. Tecnologias Utilizadas

- **Linguagem:** Python 3.x  
- **Banco de Dados:** PostgreSQL (Docker ou local)  
- **Bibliotecas Python:**
  - `psycopg2-binary`
  - `python-dotenv`
  - `uuid`

---

## 3. Como Rodar o Projeto

### 3.1. Pré-requisitos

- Python 3.x instalado
- Docker (recomendado) ou uma instância local de PostgreSQL

Subir o banco via Docker:

```bash
docker run --name pg-ecommerce \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=minhasenha123 \
  -e POSTGRES_DB=meu_ecommerce \
  -p 5432:5432 \
  -d postgres
```

---

### 3.2. Configuração do Ambiente

Clone este repositório ou baixe os arquivos.

Crie e ative um ambiente virtual (opcional, mas recomendado):

```bash
python -m venv venv
```

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

Instale as dependências:

```bash
pip install psycopg2-binary python-dotenv
```

---

### 3.3. Arquivo `.env`

Na raiz do projeto, crie um arquivo chamado `.env`:

```env
DB_NAME=meu_ecommerce
DB_USER=admin
DB_PASS=minhasenha123
DB_HOST=localhost
DB_PORT=5432
```

> **Importante:** Não commitar o `.env` no Git.

---

### 3.4. Estrutura do Banco (`init.sql`)

O arquivo `init.sql` contém a criação/reset da tabela de produtos e pedidos.  
O script Python lê esse arquivo automaticamente para **resetar o estado** a cada bateria de testes.

Certifique-se de que o `init.sql` está na mesma pasta que o script principal.

---

### 3.5. Executando a Simulação

Execute o script principal:

```bash
python simulacao_v2.py
```

> Caso o arquivo tenha outro nome (ex.: `app.py`), ajuste o comando conforme o nome real do script.

---

## 4. Entendendo os Resultados

A PoC executa diferentes cenários de concorrência. O foco principal é comparar:

### 4.1. Cenário 1: Vulnerável (Lost Update)

Implementação ingênua:

- Fluxo: **Ler → Calcular no Python → Gravar**
- Múltiplas transações leem o mesmo valor de estoque em paralelo.

Resultados típicos:

- 🔴 *Race Condition detectada*
- Vendas: **por exemplo, 8** para um estoque inicial de **5**
- Estoque final: inconsistente (possivelmente negativo ou incorreto)

---

### 4.2. Cenário 2: Seguro (Atualização Atômica)

Implementação corrigida:

- Atualização feita diretamente no banco usando uma operação atômica, por exemplo:

```sql
UPDATE produtos
SET estoque = estoque - 1
WHERE id = $1 AND estoque > 0;
```

Resultados esperados:

- 🟢 Sistema consistente
- Vendas confirmadas: exatamente **5**
- Tentativas excedentes: retornam erro do tipo **"SEM ESTOQUE"**
- Estoque final: **0**

---

## 5. Atividades

### 5.1. Análise de Problemas de Concorrência

#### 5.1.1. Inconsistência de Dados (Race Conditions)

**Fenômeno principal:** *Lost Update* (atualização perdida).

- Dois nós/leitores obtêm o mesmo valor de estoque (ex.: `1 unidade`).
- Ambos validam a compra e atualizam o valor.
- O último commit sobrescreve o anterior, ignorando a concorrência.
- **Causa raiz:** falta de atomicidade entre leitura e escrita, combinada com latência de rede em sistemas distribuídos.

#### 5.1.2. Bloqueios Prolongados (Deadlocks)

- Transações ficam presas aguardando recursos bloqueados (`WAIT`).
- Uso de **bloqueio pessimista** em cenários de alta latência mantém recursos travados por muito tempo.
- Resultado: fila de transações, gargalo e potencial colapso em horários de pico (ex.: Black Friday).

---

### 5.2. Impacto na Performance

Principais impactos operacionais:

1. **Degradação de Throughput**  
   O sistema processa menos vendas por segundo do que o hardware suporta, pois o banco gasta tempo gerenciando contenção de locks.

2. **Alta Latência**  
   Clientes percebem lentidão, *timeouts* e abandono de carrinho.

3. **Esgotamento de Recursos**  
   Transações presas ocupam o pool de conexões, levando a erros como HTTP 503 (Serviço Indisponível).

---

## 6. Proposta de Controle de Concorrência

A análise considerou diferentes estratégias clássicas para o cenário distribuído da TechLog.

### 6.1. Técnicas Avaliadas

#### 6.1.1. Two-Phase Locking (2PL)

- **Ideia:** transações passam por duas fases:
  - Crescimento: adquire todos os locks.
  - Contração: libera os locks sem poder adquirir novos.
- **Prós:**
  - Garante forte serializabilidade.
- **Contras (para Black Friday / TechLog):**
  - Alto risco de **deadlock**.
  - Leituras e escritas se bloqueiam mutuamente.
  - Performance inaceitável sob carga extrema.

---

#### 6.1.2. Timestamping (Ordenação por Carimbo de Tempo)

- **Ideia:** cada transação recebe um timestamp ao iniciar.
- Operações são validadas com base na “idade” da transação.
- **Prós:**
  - Elimina deadlocks (transações são abortadas em vez de ficarem esperando).
  - Interessante para sistemas distribuídos.
- **Contras:**
  - Risco de **starvation** para transações longas.
  - Em alta concorrência, transações complexas podem ser abortadas repetidamente.

---

#### 6.1.3. Snapshot Isolation (SI / MVCC)

- **Ideia:** uso de múltiplas versões de dados (MVCC).
  - Leituras enxergam um *snapshot* estável tirado no início da transação.
  - Escritas concorrentes em um mesmo registro geram conflito no commit (first-committer-wins).
- **Prós:**
  - Leituras não bloqueiam escritas.
  - Excelente para catálogos de produtos e navegação de usuários.
- **Contras:**
  - Possibilidade de **Write Skew** (anomalias lógicas em regras de negócio mais complexas).

---

### 6.2. Técnica Escolhida: Serializable Snapshot Isolation (SSI)

**Solução proposta para o cenário da TechLog:**  
**SSI (Serializable Snapshot Isolation)**, que combina:

- Performance do Snapshot Isolation (MVCC)
- Garantia de consistência próxima ao 2PL

**Como funciona resumidamente:**

1. Transações operam sobre *snapshots* (como em SI).
2. O banco rastreia dependências de leitura/escrita entre transações.
3. Quando detecta um padrão perigoso (grafo de dependência inconsistente), aborta uma das transações para manter o equivalente a uma execução serializável.

**Por que SSI é adequado para a TechLog (Black Friday):**

1. **Não bloqueia leituras:** catálogo continua rápido mesmo com milhares de compras concorrentes.
2. **Evita anomalias complexas:** resolve problemas que o SI puro não pega (Write Skew).
3. **Sem deadlocks clássicos:** conflitos são resolvidos via aborts, não via espera circular.
4. **Equilíbrio entre performance e integridade:** adequado para pico de vendas sem perder consistência de estoque.

---

### 6.3. Resumo Comparativo

| Critério                         | 2PL              | Timestamping     | Snapshot Isolation | SSI (Proposto)         |
|----------------------------------|------------------|------------------|--------------------|------------------------|
| Bloqueia leituras?              | Sim              | Não              | Não                | **Não**                |
| Risco de deadlock               | Alto             | Nulo             | Baixo              | **Nulo**               |
| Integridade de dados            | Total            | Total            | Parcial (Write Skew) | **Total (serializável)** |
| Adequado para Black Friday?     | Não (lento)      | Não (starvation) | Quase              | **Sim (perf + segurança)** |

---

## 7. Implementação Prática no Código

A PoC implementa uma solução de **Lock Otimista com Atualização Atômica**, complementada por **idempotência** e **constraints** de banco.

### 7.1. Atualização Atômica (Row-Level Locking Implícito)

SQL central:

```sql
UPDATE produtos
SET estoque = estoque - 1
WHERE id = $1 AND estoque > 0;
```

- O PostgreSQL adquire lock na **linha** do produto.
- Se duas transações tentam comprar o último item:
  - A primeira executa e atualiza o estoque.
  - A segunda encontra `estoque > 0` como falso e não atualiza nenhuma linha.

A aplicação interpreta “0 linhas afetadas” como **falha de compra por falta de estoque**, sem corromper o dado.

---

### 7.2. Idempotência (Proteção contra Requisições Duplicadas)

- Cada tentativa de compra gera uma **chave de idempotência** (`UUID`).
- A tabela de pedidos possui algo como:

```sql
UNIQUE (chave_idempotencia)
```

Se o cliente ou o sistema repetir a requisição:
- O banco rejeita o segundo insert.
- O estoque não é decrementado duas vezes.

---

### 7.3. Constraints de Integridade

Exemplo de constraint de segurança:

```sql
estoque INT CHECK (estoque >= 0)
```

Mesmo que a aplicação tenha bug, o banco impede estoques negativos, garantindo uma **linha de defesa extra**.

---

## 8. Recomendações para a Equipe de TI

### 8.1. Métricas de Monitoramento

- **Tempo de espera por lock (Lock Wait Time)**
- **Latência de replicação**
- **Taxa de rollback** (transações abortadas)

---

### 8.2. Tuning Dinâmico

- Ajustar **timeouts** de transação em períodos de pico (fail-fast).
- Ajustar **níveis de isolamento** em módulos não críticos para melhorar throughput.

---

### 8.3. Estratégia de Escalabilidade

- **Sharding (particionamento)** por região ou cliente.
- **Separação leitura/escrita (CQRS):**  
  leituras em réplicas, escritas no nó principal.

---

## 9. Estrutura de Arquivos

```txt
.
├── .env          # Variáveis de ambiente (NÃO COMMITAR)
├── .gitignore    # Arquivos ignorados pelo Git
├── init.sql      # Script de criação/reset de tabelas
├── app.py  # Código principal da simulação
└── README.md     # Este documento
```

