1. Análise de Problemas de Concorrência
1.1. Cenários de Conflito e Causas Raiz

Inconsistência de Dados (Race Conditions): Ocorre principalmente no cenário de "Atualização Perdida" (Lost Update).

Cenário: Dois nós distribuídos leem o saldo de um produto (ex: 1 unidade) simultaneamente. Ambos validam a compra e decrementam o valor.

Causa Raiz: Falta de atomicidade entre a leitura e a escrita, agravada pela latência da rede em sistemas distribuídos. O isolamento inadequado permite que transações sobreponham alterações.

Bloqueios Prolongados (Deadlocks):

Cenário: Transações ficam paradas em estado de espera (WAIT) aguardando a liberação de recursos (tabelas de estoque ou pedidos).

Causa Raiz: Utilização de Bloqueio Pessimista (Pessimistic Locking) em um ambiente de alta latência. Transações longas retêm os recursos ("trancam" a tabela) enquanto aguardam comunicação de rede, engarrafando todas as requisições seguintes.

1.2. Impacto na Performance do Sistema

Degradação do Throughput: O sistema processa menos vendas por segundo do que sua capacidade real, pois o banco de dados gasta recursos gerenciando filas de bloqueio em vez de efetivar transações.

Alta Latência: O tempo de resposta para o cliente final aumenta drasticamente, resultando em timeouts e abandono de carrinho.

Esgotamento de Recursos: O acúmulo de transações pendentes consome todo o pool de conexões do banco, levando a erros de "Serviço Indisponível" (HTTP 503) e negação de serviço durante picos como a Black Friday.