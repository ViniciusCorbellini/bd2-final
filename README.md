# Atividades

# **1\. Análise de Problemas de Concorrência**

# **1\. Análise de Problemas de Concorrência**

## **1.1. Cenários de Conflito e Causas Raiz**

###  **Inconsistência de Dados (Race Conditions)**

**Fenômeno Principal:** "Atualização Perdida" (*Lost Update*).

* **O Cenário:** Dois nós distribuídos leem o saldo de um produto (ex: *1 unidade*) simultaneamente. Ambos validam a compra e decrementam o valor, sobrescrevendo a operação um do outro.  
* **Causa Raiz:** Falta de **atomicidade** entre a leitura e a escrita, agravada pela latência da rede em sistemas distribuídos. O isolamento inadequado permite que transações concorrentes sobreponham alterações.

###  **Bloqueios Prolongados (Deadlocks)**

* **O Cenário:** Transações ficam paradas em estado de espera (`WAIT`) aguardando a liberação de recursos críticos (como tabelas de estoque ou pedidos).  
* **Causa Raiz:** Utilização de **Bloqueio Pessimista** (*Pessimistic Locking*) em um ambiente de alta latência. Transações longas retêm os recursos ("trancam" a tabela) enquanto aguardam a comunicação de rede, engarrafando todas as requisições seguintes na fila.

## **1.2. Impacto na Performance do Sistema**

A combinação das falhas acima gera os seguintes impactos operacionais:

1.  **Degradação do Throughput** O sistema processa menos vendas por segundo do que sua capacidade real de hardware, pois o banco de dados gasta recursos gerenciando filas de bloqueio (*Lock Contention*) em vez de efetivar transações.  
2.  **Alta Latência** O tempo de resposta para o cliente final aumenta drasticamente, resultando em *timeouts* de aplicação e abandono de carrinho de compras.  
3.  **Esgotamento de Recursos** O acúmulo de transações pendentes consome todo o *pool* de conexões do banco de dados, levando a erros de **"Serviço Indisponível" (HTTP 503\)** e negação de serviço durante picos de acesso (Black Friday).

# **2\. Proposta de Controle de Concorrência**

Para mitigar os riscos identificados, avaliamos três estratégias clássicas de controle de concorrência.

## **2.1. Análise Comparativa de Técnicas**

###  **Bloqueio em Dois Níveis (Two-Phase Locking – 2PL)**

* **Conceito:** Garante serialização estrita dividindo a transação em duas fases: crescimento (adquire todos os locks necessários) e encolhimento (libera os locks).  
* **Avaliação:** **Inviável** para a TechLog. Em sistemas distribuídos com alta latência, o 2PL mantém recursos bloqueados por muito tempo, causando *deadlocks* frequentes e derrubando a performance na Black Friday.

###  **Timestamping (Ordenação por Carimbo de Tempo)**

* **Conceito:** Atribui um carimbo de tempo único para cada transação. O sistema aborta qualquer operação que tente alterar um dado "mais novo" com uma transação "mais antiga".  
* **Avaliação:** **Essencial como componente**. Sozinho pode ser complexo devido à sincronização de relógios, mas é fundamental quando combinado com controle de versão.

###  **Snapshot Isolation (Isolamento de Instantâneo)**

* **Conceito:** A transação opera em uma "versão" (foto) dos dados tirada no início da operação. Leituras nunca bloqueiam escritas, e escritas nunca bloqueiam leituras.  
* **Avaliação:** **Ideal**. Permite alta concorrência sem sacrificar a consistência.

## **2.2. Solução Escolhida e Justificativa**

**Técnica Selecionada:** **Snapshot Isolation com Timestamping**.

**Justificativa para o Ambiente TechLog:**

1. **Ordenação Temporal Consistente:** O uso de **Timestamping** atribui marcas temporais precisas (Início e Commit) para cada transação. Isso permite que o banco de dados ordene logicamente os eventos no sistema distribuído, garantindo que cada transação "enxergue" apenas os dados válidos no seu instante de início (Snapshot), sem interferência de modificações futuras.  
2. **Detecção de Conflitos (First-Committer-Wins):** A combinação utiliza o timestamp para aplicar a regra do "Primeiro a Comitar Vence". Se duas transações concorrentes tentam modificar o mesmo dado (baseadas no mesmo snapshot inicial), o sistema compara os timestamps de commit. A segunda transação detecta que o dado já possui um timestamp mais recente do que o seu snapshot de leitura e falha automaticamente, prevenindo a "Atualização Perdida" sem necessidade de bloqueios prévios.  
3. **Performance de Leitura na Black Friday:** Como as leituras são baseadas em timestamps passados (snapshots), elas nunca são bloqueadas por locks de escrita. Isso garante que a navegação pelo catálogo e a consulta de preços permaneçam rápidas, mesmo enquanto o sistema processa milhares de atualizações de estoque.

