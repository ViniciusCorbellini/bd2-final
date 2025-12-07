import psycopg2
import threading
import time
import queue
import random
import uuid # Biblioteca para gerar IDs únicos universais
import os

from dotenv import load_dotenv 

# ========== consumindo o .env ==========
load_dotenv()
# =======================================

# CONFIGURAÇÃO DE CONEXÃO 
DB_URI = os.getenv("DATABASE_URL")

def get_db_connection():
    # Pega a URL definida no docker-compose.yml
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        raise ValueError("A variável DATABASE_URL não está definida!")

    print(f"🔌 Tentando conectar em: {db_url}...")
    
    # Loop simples de retentativa, caso o banco demore milissegundos a mais
    for i in range(5):
        try:
            conn = psycopg2.connect(db_url)
            return conn
        except psycopg2.OperationalError as e:
            print(f"⏳ Banco ainda indisponível, tentando novamente ({i+1}/5)...")
            time.sleep(20)
    
    raise Exception("❌ Não foi possível conectar ao banco após várias tentativas.")

fila_pedidos = queue.Queue()

# --- A STORED PROCEDURE INTELIGENTE (ADAPTADA AO NOVO SQL) ---
def stored_procedure_segura(cliente_id, transaction_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. VERIFICAÇÃO DE IDEMPOTÊNCIA (Adaptação para tabela 'pedidos')
        try:
            # Mapeamento: transaction_id -> chave_idempotencia
            # Assumindo sempre produto 1 e quantidade 1 para este teste
            cursor.execute(
                """
                INSERT INTO pedidos 
                (chave_idempotencia, cliente_id, id_produto, quantidade, status) 
                VALUES (%s, %s, 1, 1, 'PROCESSANDO')
                """,
                (transaction_id, cliente_id)
            )
        except psycopg2.IntegrityError:
            conn.rollback()
            print(f"⚠️ [DB] Bloqueio: Pedido duplicado detectado (UUID: {transaction_id})!")
            return

        # 2. BLOQUEIO DE LINHA (FOR UPDATE)
        cursor.execute("SELECT estoque FROM produtos WHERE id = 1 FOR UPDATE")
        resultado = cursor.fetchone()
        
        if resultado:
            estoque = resultado[0]
            if estoque > 0:
                # Decrementa estoque
                cursor.execute("UPDATE produtos SET estoque = estoque - 1 WHERE id = 1")
                
                # Atualiza status na tabela 'pedidos'
                cursor.execute(
                    "UPDATE pedidos SET status = 'SUCESSO' WHERE chave_idempotencia = %s", 
                    (transaction_id,)
                )
                conn.commit()
                print(f"✅ [DB] Venda Aprovada. Cliente {cliente_id}.")
            else:
                # Falha por sem estoque
                cursor.execute(
                    "UPDATE pedidos SET status = 'FALHA_SEM_ESTOQUE' WHERE chave_idempotencia = %s", 
                    (transaction_id,)
                )
                conn.commit()
                print(f"🚫 [DB] Sem estoque. Cliente {cliente_id}.")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro Crítico: {e}")
    finally:
        cursor.close()
        conn.close()

# --- API (SIMULAÇÃO) ---
def api_receber_pedido(cliente_id):
    transacao_unica_id = str(uuid.uuid4())
    pacote = { "cliente_id": cliente_id, "transaction_id": transacao_unica_id }
    fila_pedidos.put(pacote)

    # Simula clique duplo (Retry acidental do frontend)
    if random.random() < 0.7:
        print(f"⚡ [API] Cliente {cliente_id} clicou 2x! Enviando duplicata...")
        fila_pedidos.put(pacote)

# --- WORKER ---
def worker_backend(i):
    while True:
        try:
            pacote = fila_pedidos.get(timeout=3)
        except queue.Empty:
            break
        
        stored_procedure_segura(pacote["cliente_id"], pacote["transaction_id"])
        fila_pedidos.task_done()

# --- EXECUÇÃO ---
def rodar():
    print("\n--- INICIANDO SISTEMA DE PEDIDOS (IDEMPOTENTE) ---")
    
    # Aguarda o banco acordar (caso o container esteja subindo agora)
    time.sleep(5) 

    threads = []
    # 1. Gera carga de pedidos (15 pedidos para 10 itens de estoque)
    for i in range(15):
        t = threading.Thread(target=api_receber_pedido, args=(i,))
        threads.append(t)
        t.start()
    for t in threads: t.join()

    # 2. Processa com Workers
    workers = []
    for i in range(4):
        t = threading.Thread(target=worker_backend, args=(i,))
        workers.append(t)
        t.start()
    for t in workers: t.join()

    # 3. Auditoria Final
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Conta sucessos na tabela 'pedidos'
        cursor.execute("SELECT count(*) FROM pedidos WHERE status='SUCESSO'")
        vendas = cursor.fetchone()[0]
        
        # Verifica estoque restante
        cursor.execute("SELECT estoque FROM produtos WHERE id=1")
        estoque = cursor.fetchone()[0]
        
        print("\n" + "="*40)
        print("RELATÓRIO FINAL DE CONSISTÊNCIA")
        print("="*40)
        print(f"📦 Estoque Inicial: 10") # Sabemos que o init.sql insere 10
        print(f"💰 Vendas Realizadas: {vendas}")
        print(f"📉 Estoque Final no DB: {estoque}")
        print("-" * 40)
        
        if vendas + estoque == 10:
            print("✅ SUCESSO: A soma bate perfeitamente! (Consistência ACID)")
        else:
            print("❌ PERIGO: O dinheiro sumiu ou o estoque multiplicou!")
            
        conn.close()
    except Exception as e:
        print(f"Erro na auditoria: {e}")

if __name__ == "__main__":
    rodar()