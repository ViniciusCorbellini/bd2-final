## **2\. Proposta de Controle de Concorrência**

Para resolver os problemas de bloqueios, latência e inconsistência no ambiente distribuído da TechLog, analisamos quatro técnicas distintas de controle de concorrência. Abaixo, detalhamos o funcionamento de cada uma, avaliando sua viabilidade para o cenário de alta demanda (Black Friday).

### **2.1. Bloqueio em Dois Níveis (Two-Phase Locking – 2PL)**

É a técnica mais tradicional de controle pessimista, focada em garantir a serializabilidade estrita através do bloqueio físico de recursos.

* **Como funciona:** A transação ocorre em duas fases rígidas.  
  1. **Fase de Expansão:** A transação acumula todos os bloqueios (locks) de leitura ou escrita necessários. Nenhuma operação é executada até que todos os recursos estejam travados.  
  2. **Fase de Contração:** Após processar, a transação começa a liberar os bloqueios. Uma vez que o primeiro bloqueio é liberado, nenhum novo bloqueio pode ser adquirido.

#### **Análise para o Cenário TechLog**

* **Prós:**  
  * **Consistência Robusta:** Garante matematicamente que não haverá conflitos de escrita. Impede venda duplicada de estoque de forma eficaz.  
* **Contras (Críticos):**  
  * **Alto Risco de Deadlock:** Em alta demanda, a chance de transações ficarem esperando umas pelas outras (travamento cruzado) é altíssima.  
  * **Baixa Performance:** Leituras bloqueiam escritas. Um cliente consultando um produto pode impedir que outro finalize a compra, causando lentidão inaceitável na Black Friday.

---

### **2.2. Timestamping (Ordenação por Carimbo de Tempo)**

Uma técnica otimista que elimina bloqueios (lock-free), decidindo a prioridade com base na "idade" da transação.

* **Como funciona:** Cada transação recebe um *timestamp* (TS) ao iniciar. O banco valida cada operação comparando o TS da transação com o TS da última leitura/escrita do dado.  
  * Se uma transação "mais velha" tenta escrever em um dado já acessado por uma transação "mais nova", a transação velha é abortada e reiniciada.

#### **Análise para o Cenário TechLog**

* **Prós:**  
  * **Eliminação de Deadlocks:** Como não há espera por recursos (a transação ou passa ou morre), o sistema não trava.  
  * **Bom para Distribuídos:** Remove a necessidade de um gerenciador global de *locks* complexo.  
* **Contras (Críticos):**  
  * **Starvation (Fome):** Em cenários de concorrência extrema, transações longas (como um relatório de vendas ou um pedido com muitos itens) podem ser abortadas repetidamente por transações menores e mais rápidas, nunca conseguindo finalizar.

---

### **2.3. Snapshot Isolation (Isolamento de Snapshot / MVCC)**

Utiliza o conceito de múltiplas versões dos dados (MVCC) para permitir que leitores e escritores operem simultaneamente sem se bloquearem.

* **Como funciona:**  
  * **Leitura:** A transação vê uma "foto" (snapshot) do banco no momento em que começou. Ela ignora mudanças feitas por outras transações concorrentes.  
  * **Escrita:** Se duas transações tentarem alterar *o mesmo registro* simultaneamente, a primeira a comitar vence ("First Committer Wins"); a segunda é abortada.

#### **Análise para o Cenário TechLog**

* **Prós:**  
  * **Alta Disponibilidade de Leitura:** Leitores nunca bloqueiam escritores. Isso resolveria a lentidão na navegação do catálogo da TechLog.  
* **Contras (Críticos):**  
  * **Anomalia de Write Skew:** Permite inconsistências lógicas quando duas transações leem dados diferentes mas violam uma regra de negócio conjunta (ex: vender estoque baseado em uma leitura desatualizada de orçamento). Isso exigiria validações complexas no código da aplicação.

---

### **2.4. Técnica Escolhida: Serializable Snapshot Isolation (SSI)**

A solução proposta para a TechLog é a **SSI**. Esta técnica representa o estado da arte em bancos de dados modernos, combinando a performance do Snapshot com a segurança do 2PL.

* Como funciona (A "Mescla"):  
  O SSI utiliza o mecanismo de MVCC (versões por timestamp) para leituras não bloqueantes, mas adiciona uma camada de detecção de conflitos no grafo de dependências.  
  1. As transações rodam em *snapshots* isolados (rápido).  
  2. O banco monitora "quem leu o quê" e "quem alterou o quê".  
  3. Se o banco detectar um padrão de "leitura-escrita" perigoso (onde uma transação ignora a escrita da outra de forma que geraria inconsistência), ele aborta uma das transações preventivamente.

#### **Justificativa da Escolha para a TechLog**

Optamos pelo **SSI** pois ele ataca diretamente os quatro problemas identificados no cenário:

1. **Resolve Bloqueios Prolongados:** Ao contrário do 2PL, o SSI não bloqueia leituras. Clientes podem navegar nas promoções livremente sem travar o checkout de outros.  
2. **Resolve Falhas de Consistência (Write Skew):** Diferente do Snapshot Isolation puro, o SSI detecta e impede anomalias complexas de regras de negócio automaticamente, garantindo integridade total do estoque.  
3. **Gerencia Sobrecarga:** Embora possa gerar *aborts* (que exigem retry automático), é muito mais leve que gerenciar *deadlocks* em uma rede distribuída.  
4. **Melhora a Experiência do Cliente:** O sistema permanece responsivo (baixa latência) mesmo sob alta carga, pois a contenção ocorre apenas no momento do *commit*, não durante a navegação.

---

### **Resumo Comparativo**

| Critério | 2PL | Timestamping | Snapshot Isolation | SSI (Proposto) |
| :---- | :---- | :---- | :---- | :---- |
| **Bloqueia Leituras?** | Sim (Alto impacto) | Não | Não | **Não** |
| **Risco de Deadlock** | Alto | Nulo | Baixo | **Nulo** |
| **Integridade de Dados** | Total | Total | Parcial (Risco de Write Skew) | **Total (Serializável)** |
| **Ideal para Black Friday?** | Não (Lento) | Não (Starvation) | Quase (Risco de erros) | **Sim (Performance \+ Segurança)** |

