import psycopg2
import threading
import time
import queue
import random
import uuid # Biblioteca para gerar IDs únicos universais
import os
from psycopg2 import sql
from dotenv import load_dotenv 

# ========== consumindo o .env ==========
load_dotenv()

# CONFIGURAÇÃO DE CONEXÃO 
DB_URI = os.getenv("SUPABASE_DATABASE_URL")

# Verificação de segurança simples
if not DB_URI:
    raise ValueError("Erro: A variável SUPABASE_DATABASE_URL não foi encontrada no arquivo .env")
# =======================================


# --- conexão  ---
def get_db_connection():
    # O psycopg2 é inteligente o suficiente para ler a URI completa
    return psycopg2.connect(DB_URI)

fila_pedidos = queue.Queue()

def setup_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Limpeza (Cuidado em produção!)
    cursor.execute('DROP TABLE IF EXISTS produtos')
    cursor.execute('DROP TABLE IF EXISTS historico_transacoes')

    # Criação das tabelas (Sintaxe Postgres)
    cursor.execute('CREATE TABLE produtos (id SERIAL PRIMARY KEY, estoque INTEGER)')

    cursor.execute('''
        CREATE TABLE historico_transacoes (
            transaction_id TEXT PRIMARY KEY,
            cliente_id INTEGER,
            status TEXT,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute("INSERT INTO produtos (id, estoque) VALUES (1, 5)")
    conn.commit()
    conn.close()
    print("✅ [SETUP] Banco Supabase configurado.")

# --- A STORED PROCEDURE INTELIGENTE ---
def stored_procedure_segura(cliente_id, transaction_id):
    # Cada thread abre sua própria conexão (Importante para concorrência!)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. VERIFICAÇÃO DE IDEMPOTÊNCIA
        # Tenta inserir o "Crachá" da transação.
        try:
            cursor.execute(
                "INSERT INTO historico_transacoes (transaction_id, cliente_id, status) VALUES (%s, %s, 'PROCESSANDO')",
                (transaction_id, cliente_id)
            )
        except psycopg2.IntegrityError:
            # ID duplicado detectado
            conn.rollback() # Limpa o erro da transação atual
            print(f"⚠️ [DB] Bloqueio: Transação {transaction_id[:8]}... duplicada!")
            return

        # 2. BLOQUEIO DE LINHA (A Mágica do Postgres)
        # 'FOR UPDATE' trava APENAS a linha do produto id=1 até o commit/rollback.
        # Outras threads que tentarem ler essa linha vão esperar na fila aqui.
        cursor.execute("SELECT estoque FROM produtos WHERE id = 1 FOR UPDATE")
        resultado = cursor.fetchone()
        
        if resultado:
            estoque = resultado[0]
            if estoque > 0:
                cursor.execute("UPDATE produtos SET estoque = estoque - 1 WHERE id = 1")
                cursor.execute("UPDATE historico_transacoes SET status = 'SUCESSO' WHERE transaction_id = %s", (transaction_id,))
                conn.commit()
                print(f"✅ [DB] Venda Aprovada. Cliente {cliente_id}.")
            else:
                cursor.execute("UPDATE historico_transacoes SET status = 'FALHA_SEM_ESTOQUE' WHERE transaction_id = %s", (transaction_id,))
                conn.commit()
                print(f"🚫 [DB] Sem estoque. Cliente {cliente_id}.")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro Crítico: {e}")
    finally:
        cursor.close()
        conn.close()

# --- API (BACKEND) ---
def api_receber_pedido(cliente_id):
    transacao_unica_id = str(uuid.uuid4())
    pacote = { "cliente_id": cliente_id, "transaction_id": transacao_unica_id }
    fila_pedidos.put(pacote)

    # Simula clique duplo (30% de chance)
    if random.random() < 0.3:
        print(f"⚡ [API] Cliente {cliente_id} clicou 2x! Enviando duplicata...")
        fila_pedidos.put(pacote)

# --- WORKER ---
def worker_backend(i):
    while True:
        try:
            pacote = fila_pedidos.get(timeout=3) # Timeout maior por causa da latência de rede
        except queue.Empty:
            break
        
        # Processa
        stored_procedure_segura(pacote["cliente_id"], pacote["transaction_id"])
        fila_pedidos.task_done()

# --- EXECUÇÃO ---
def rodar():
    print("\n--- INICIANDO SISTEMA COM SUPABASE (POSTGRES) ---")
    setup_db()

    threads = []
    # Cria pedidos
    for i in range(10):
        t = threading.Thread(target=api_receber_pedido, args=(i,))
        threads.append(t)
        t.start()
    for t in threads: t.join()

    # Workers processam
    workers = []
    for i in range(4): # Aumentei para 4 workers para testar mais concorrência
        t = threading.Thread(target=worker_backend, args=(i,))
        workers.append(t)
        t.start()
    for t in workers: t.join()

    # Auditoria Final
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM historico_transacoes WHERE status='SUCESSO'")
    sucessos = cursor.fetchone()[0]
    cursor.execute("SELECT estoque FROM produtos WHERE id=1")
    estoque = cursor.fetchone()[0]
    
    print("\n--- RESULTADO FINAL SUPABASE ---")
    print(f"Vendas Reais: {sucessos}")
    print(f"Estoque Final: {estoque}")
    conn.close()

if __name__ == "__main__":
    rodar()