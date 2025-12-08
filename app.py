import os
import time
import uuid
import random
import queue
import threading

from psycopg2.pool import SimpleConnectionPool
from psycopg2 import extensions, IntegrityError, OperationalError
from dotenv import load_dotenv

# =========================
# Carregar variáveis de ambiente
# =========================
load_dotenv()

DB_URI = os.getenv("DATABASE_URL")
if not DB_URI:
    raise ValueError("A variável DATABASE_URL não está definida!")

# =========================
# Pool de conexões global
# =========================
pool: SimpleConnectionPool | None = None

def init_connection_pool():
    """
    Inicializa o pool de conexões com retry.
    Isso evita abrir/fechar conexão a cada requisição.
    """
    global pool
    last_error: Exception | None = None

    print("Inicializando pool de conexões com o banco de dados...")

    for i in range(10):
        try:
            pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=DB_URI,
            )
            print("Pool de conexões inicializado com sucesso.")
            return
        except OperationalError as e:
            last_error = e
            print(f"Banco indisponível, tentativa {i + 1}/10...")
            time.sleep(3)

    raise Exception(f"Não foi possível inicializar o pool: {last_error}")

def get_db_connection():
    """
    Obtém uma conexão do pool já configurada com isolamento SERIALIZABLE.
    """
    if pool is None:
        raise RuntimeError("Pool de conexões não inicializado. Chame init_connection_pool() antes.")

    conn = pool.getconn()
    # Configura a sessão para usar Serializable Snapshot Isolation
    conn.set_session(
        isolation_level=extensions.ISOLATION_LEVEL_SERIALIZABLE,
        readonly=False,
        autocommit=False,
    )
    return conn

def release_db_connection(conn):
    """
    Devolve a conexão ao pool.
    """
    if pool is not None and conn is not None:
        pool.putconn(conn)

# =========================
# Fila de pedidos (simulação de fila de mensageria)
# =========================
fila_pedidos: "queue.Queue[dict]" = queue.Queue()

# =========================
# Métricas simples de monitoramento
# =========================
metricas = {
    "pedidos_processados": 0,
    "pedidos_duplicados": 0,
    "pedidos_sem_estoque": 0,
    "tempo_total_processamento": 0.0,
}

metricas_lock = threading.Lock()

# =========================
# Stored procedure "segura"
# =========================
def stored_procedure_segura(cliente_id: int, transaction_id: str):
    """
    Simula uma stored procedure transacional com:
      - Idempotência via chave_idempotencia (UNIQUE)
      - Atualização atômica de estoque
      - Isolamento SERIALIZABLE (SSI no PostgreSQL)
    """
    inicio = time.time()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Verificação de idempotência
        try:
            # Mapeamento: transaction_id -> chave_idempotencia
            # Assumindo sempre produto 1 e quantidade 1 para este teste
            cursor.execute(
                """
                INSERT INTO pedidos 
                  (chave_idempotencia, cliente_id, id_produto, quantidade, status) 
                VALUES 
                  (%s, %s, 1, 1, 'PROCESSANDO')
                """,
                (transaction_id, cliente_id),
            )
        except IntegrityError:
            conn.rollback()
            with metricas_lock:
                metricas["pedidos_duplicados"] += 1
            print(f"[DB] Pedido duplicado detectado (UUID: {transaction_id})! Ignorando retry.")
            return

        # 2. Atualização atômica do estoque
        # Tenta decrementar estoque apenas se estoque > 0
        cursor.execute(
            """
            UPDATE produtos
               SET estoque = estoque - 1
             WHERE id = 1
               AND estoque > 0
         RETURNING estoque;
            """
        )
        row = cursor.fetchone()

        if row is None:
            # Nenhuma linha atualizada → sem estoque
            cursor.execute(
                """
                UPDATE pedidos 
                   SET status = 'FALHA_SEM_ESTOQUE'
                 WHERE chave_idempotencia = %s
                """,
                (transaction_id,),
            )
            conn.commit()
            with metricas_lock:
                metricas["pedidos_sem_estoque"] += 1
            print(f"[DB] Sem estoque. Cliente {cliente_id}.")
        else:
            # Estoque decrementado com sucesso
            cursor.execute(
                """
                UPDATE pedidos 
                   SET status = 'SUCESSO'
                 WHERE chave_idempotencia = %s
                """,
                (transaction_id,),
            )
            conn.commit()
            with metricas_lock:
                metricas["pedidos_processados"] += 1
            print(f"[DB] Venda aprovada. Cliente {cliente_id}. Estoque atual: {row[0]}")

    except Exception as e:
        conn.rollback()
        print(f"Erro Crítico na stored_procedure_segura: {e}")
    finally:
        duracao = time.time() - inicio
        with metricas_lock:
            metricas["tempo_total_processamento"] += duracao
        cursor.close()
        release_db_connection(conn)

# =========================
# API fake (simula frontend/proxy mandando pedidos)
# =========================
def api_receber_pedido(cliente_id: int):
    """
    Simula o recebimento de um pedido vindo de um cliente.
    Gera um UUID por transação e, em 70% dos casos, simula clique duplo/retry.
    """
    transacao_unica_id = str(uuid.uuid4())
    pacote = {"cliente_id": cliente_id, "transaction_id": transacao_unica_id}
    fila_pedidos.put(pacote)

    # Simula clique duplo / retry
    if random.random() < 0.7:
        print(f"[API] Cliente {cliente_id} clicou 2x! Enviando duplicata...")
        fila_pedidos.put(pacote)

# =========================
# Worker de backend (simula nó de aplicação processando fila)
# =========================
def worker_backend(worker_id: int):
    while True:
        try:
            pacote = fila_pedidos.get(timeout=3)
        except queue.Empty:
            # Nada mais para processar
            break

        stored_procedure_segura(pacote["cliente_id"], pacote["transaction_id"])
        fila_pedidos.task_done()

# =========================
# Execução principal
# =========================
def rodar():
    print("\n--- INICIANDO SISTEMA DE PEDIDOS (IDEMPOTENTE + SSI) ---")

    # 1. Inicializa pool de conexões
    init_connection_pool()

    # 2. Gera carga de pedidos (15 pedidos para estoque inicial 10, assumido no init.sql)
    threads_api: list[threading.Thread] = []
    for i in range(15):
        t = threading.Thread(target=api_receber_pedido, args=(i,))
        threads_api.append(t)
        t.start()

    for t in threads_api:
        t.join()

    # 3. Processa com workers (simulando múltiplos nós de backend)
    workers: list[threading.Thread] = []
    for i in range(4):
        t = threading.Thread(target=worker_backend, args=(i,))
        workers.append(t)
        t.start()

    for t in workers:
        t.join()

    # 4. Auditoria final no banco
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Conta sucessos na tabela 'pedidos'
        cursor.execute("SELECT count(*) FROM pedidos WHERE status = 'SUCESSO'")
        vendas = cursor.fetchone()[0]

        # Verifica estoque restante
        cursor.execute("SELECT estoque FROM produtos WHERE id = 1")
        estoque = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        release_db_connection(conn)

        print("\n" + "=" * 40)
        print("RELATÓRIO FINAL DE CONSISTÊNCIA")
        print("=" * 40)
        print(f"Estoque Inicial: 10  (assumido pelo init.sql)")
        print(f"Vendas Realizadas (SUCESSO): {vendas}")
        print(f"Estoque Final no DB: {estoque}")
        print("-" * 40)

        if vendas + estoque == 10:
            print("SUCESSO: A soma bate perfeitamente! (Consistência preservada)")
        else:
            print("PERIGO: Inconsistência detectada! (dinheiro sumiu ou estoque multiplicou)")

        # Métricas adicionais
        print("\nMÉTRICAS DE EXECUÇÃO")
        print("-" * 40)
        with metricas_lock:
            pedidos_ok = metricas["pedidos_processados"]
            pedidos_dup = metricas["pedidos_duplicados"]
            pedidos_sem = metricas["pedidos_sem_estoque"]
            tempo_total = metricas["tempo_total_processamento"]
        total_tratados = pedidos_ok + pedidos_dup + pedidos_sem

        print(f"Pedidos únicos processados: {pedidos_ok}")
        print(f"Pedidos duplicados (idempotência): {pedidos_dup}")
        print(f"Pedidos sem estoque: {pedidos_sem}")
        print(f"Total de eventos tratados (incluindo retries bloqueados): {total_tratados}")
        if pedidos_ok > 0:
            print(f"Tempo médio por pedido único: {tempo_total / pedidos_ok:.4f}s")

    except Exception as e:
        print(f"Erro na auditoria final: {e}")

if __name__ == "__main__":
    rodar()
