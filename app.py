import sqlite3
import threading
import time
import queue
import random
import uuid # Biblioteca para gerar IDs únicos universais

fila_pedidos = queue.Queue()

def setup_db():
    conn = sqlite3.connect('techlog_idempotente.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS produtos')
    cursor.execute('DROP TABLE IF EXISTS historico_transacoes')

    # Tabela de Produtos
    cursor.execute('CREATE TABLE produtos (id INTEGER PRIMARY KEY, estoque INTEGER)')

    # Tabela para "Lembrar" dos IDs (A memória do banco)
    # O campo 'transaction_id' deve ser UNIQUE para o banco bloquear duplicatas automaticamente
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
    return conn

# --- A STORED PROCEDURE INTELIGENTE ---
# Agora ela recebe o 'transaction_id' gerado pelo backend
def stored_procedure_segura(conn, cliente_id, transaction_id):
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN EXCLUSIVE TRANSACTION")

        # 1. VERIFICAÇÃO DE IDEMPOTÊNCIA (A Comparação de IDs)
        # Tenta inserir o ID da transação. Se já existir, o banco gera erro de INTEGRITY.
        try:
            cursor.execute("INSERT INTO historico_transacoes (transaction_id, cliente_id, status) VALUES (?, ?, 'PROCESSANDO')", (transaction_id, cliente_id))
        except sqlite3.IntegrityError:
            # Se caiu aqui, é porque o ID já existe!
            conn.rollback()
            print(f"⚠️ [DB] Bloqueio: Transação {transaction_id} duplicada detectada!")
            return

        # 2. Lógica de Negócio (Estoque)
        cursor.execute("SELECT estoque FROM produtos WHERE id = 1")
        estoque = cursor.fetchone()[0]

        if estoque > 0:
            cursor.execute("UPDATE produtos SET estoque = estoque - 1 WHERE id = 1")
            # Atualiza o status da transação para sucesso
            cursor.execute("UPDATE historico_transacoes SET status = 'SUCESSO' WHERE transaction_id = ?", (transaction_id,))
            conn.commit()
            print(f"✅ [DB] Venda Aprovada. Cliente {cliente_id}. ID Transação: {transaction_id[:8]}...")
        else:
            cursor.execute("UPDATE historico_transacoes SET status = 'FALHA_SEM_ESTOQUE' WHERE transaction_id = ?", (transaction_id,))
            conn.commit()
            print(f"🚫 [DB] Sem estoque. Cliente {cliente_id}.")

    except Exception as e:
        conn.rollback()
        print(f"Erro Crítico: {e}")

# --- API (BACKEND) ---
def api_receber_pedido(cliente_id):
    # O Backend gera o ID Único. Isso é o "Crachá" da transação.
    transacao_unica_id = str(uuid.uuid4())

    pacote = {
        "cliente_id": cliente_id,
        "transaction_id": transacao_unica_id
    }
    fila_pedidos.put(pacote)

    # SIMULAÇÃO DE ERRO DE DUPLA REQUISIÇÃO (Usuário impaciente clicou 2x)
    # Vamos enviar o MESMO pacote de novo para a fila para testar a segurança
    if random.random() < 0.3: # 30% de chance de duplicar
        print(f"⚡ [API] Cliente {cliente_id} clicou 2x! Enviando duplicata...")
        fila_pedidos.put(pacote)

# --- WORKER ---
def worker_backend(i):
    conn = sqlite3.connect('techlog_idempotente.db', check_same_thread=False)
    while True:
        try:
            pacote = fila_pedidos.get(timeout=2)
        except queue.Empty:
            break

        time.sleep(0.05)
        # Manda para o banco validar o ID
        stored_procedure_segura(conn, pacote["cliente_id"], pacote["transaction_id"])
        fila_pedidos.task_done()
    conn.close()

# --- EXECUÇÃO ---
def rodar():
    print("\n--- INICIANDO SISTEMA COM IDEMPOTÊNCIA (PROTEÇÃO TOTAL) ---")
    setup_db()

    # Clientes gerando pedidos
    threads = []
    for i in range(10):
        t = threading.Thread(target=api_receber_pedido, args=(i,))
        threads.append(t)
        t.start()
    for t in threads: t.join()

    # Workers processando
    workers = []
    for i in range(2):
        t = threading.Thread(target=worker_backend, args=(i,))
        workers.append(t)
        t.start()
    for t in workers: t.join()

    # Auditoria
    conn = sqlite3.connect('techlog_idempotente.db')
    cursor = conn.cursor()
    sucessos = cursor.execute("SELECT count(*) FROM historico_transacoes WHERE status='SUCESSO'").fetchone()[0]
    duplicadas = cursor.execute("SELECT count(*) FROM historico_transacoes").fetchone()[0]
    estoque = cursor.execute("SELECT estoque FROM produtos").fetchone()[0]

    print("\n--- RESULTADO ---")
    print(f"Vendas Reais: {sucessos}")
    print(f"Estoque Final: {estoque}")
    print(f"Total de Transações Processadas (Únicas): {duplicadas}")
    print("(Se houveram cliques duplos, eles foram ignorados e não aparecem como vendas extras)")
    conn.close()

if __name__ == "__main__":
    rodar()