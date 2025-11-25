# Atividades

# **1\. Análise de Problemas de Concorrência**

Esta seção detalha o diagnóstico técnico dos conflitos identificados no ambiente distribuído da TechLog.

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

