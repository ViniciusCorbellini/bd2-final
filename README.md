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
`
docker run --name pg-ecommerce \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=minhasenha123 \
  -e POSTGRES_DB=meu_ecommerce \
  -p 5432:5432 \
  -d postgres
`

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
├── .env               # Variáveis de ambiente (Senhas) - NÃO COMMITE ISSO
├── .gitignore         # Arquivos para o Git ignorar
├── init.sql           # Script de criação/reset das tabelas
├── simulacao_v2.py    # Código principal da simulação
└── README.md          # Documentação
