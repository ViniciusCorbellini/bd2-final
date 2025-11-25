## Recomendações para a Equipe de TI: Monitoramento e Ajuste de Escala

Para garantir a estabilidade do sistema distribuído da TechLog conforme a demanda cresça, recomenda-se focar nestes três pilares:

### 1. Métricas de Monitoramento (O que observar)
* **Tempo de Espera por Bloqueio (*Lock Wait Time*):** Configurar alertas para picos no tempo de espera. Valores altos indicam gargalos críticos na concorrência.
* **Latência de Replicação:** Monitorar o atraso (*lag*) na propagação de dados entre os nós. Atrasos elevados comprometem a consistência dos dados para o utilizador final.
* **Taxa de *Rollback*:** Acompanhar o volume de transações revertidas. Um aumento repentino sinaliza excesso de conflitos simultâneos pelo mesmo recurso.

### 2. Ajustes Dinâmicos (*Tuning*)
* **Timeouts Agressivos:** Em períodos de alta demanda (como Black Friday), reduzir os *timeouts* das transações para libertar recursos travados mais rapidamente (*fail-fast*), evitando o efeito cascata.
* **Nível de Isolamento:** Avaliar a redução temporária do isolamento (ex: de *Serializable* para *Read Committed*) em módulos não críticos (como rastreamento de carga) para aumentar a vazão do sistema.

### 3. Estratégia de Crescimento (Escalabilidade)
* ***Sharding* (Particionamento):** Caso um nó atinja a saturação, dividir os dados horizontalmente (por região ou ID de cliente) para distribuir a carga de escrita e reduzir bloqueios.
* **Segregação de Leitura/Escrita (CQRS):** Direcionar relatórios pesados e consultas de histórico exclusivamente para réplicas de leitura, preservando o nó principal para transações críticas.