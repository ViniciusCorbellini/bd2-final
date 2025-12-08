-- init.sql
DROP TABLE IF EXISTS pedidos;
DROP TABLE IF EXISTS produtos;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Tabela de Produtos (O recurso escasso)
CREATE TABLE produtos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100),
    estoque INT CHECK (estoque >= 0), -- A trava nativa (opcional, se quiser ver o erro explodir)
    versao INT DEFAULT 1 -- Útil para Optimistic Locking
);

-- Tabela de Pedidos (O histórico)
CREATE TABLE pedidos (
    id SERIAL PRIMARY KEY,
    id_produto INT REFERENCES produtos(id),
    cliente_id INT,
    chave_idempotencia UUID UNIQUE, -- Garante que não haja pedidos duplicados
    quantidade INT,
    status VARCHAR(20) DEFAULT 'PENDENTE',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Inserindo um produto com 10 unidades
INSERT INTO produtos (id, nome, estoque) VALUES (1, 'Samsung Galaxy A56 256 Gb', 10);