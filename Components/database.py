import sqlite3
import sys
from tkinter import messagebox

from .config import APP_DIR, DB_NAME


def criar_banco():
    # Código da função criar_banco (mantido inalterado)
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS os (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT,
                cliente TEXT,
                telefone TEXT,
                modelo TEXT,
                imei TEXT,
                senha TEXT,
                acessorios TEXT,
                problemas TEXT,
                situacao TEXT,
                valor TEXT,
                entrada TEXT,
                saida TEXT,
                garantia TEXT,
                arquivo TEXT,
                tipo_garantia TEXT,
                metodo_pagamento TEXT,
                checklist TEXT,
                dias_garantia INTEGER,
                tipo_documento TEXT
            )
            """
        )
        conn.commit()

        # Verificar colunas e adicionar caso faltem (MIGRAÇÃO)
        c.execute("PRAGMA table_info(os)")
        cols = [row[1] for row in c.fetchall()]

        obrig = {
            "garantia": "TEXT",
            "saida": "TEXT",
            "tipo_garantia": "TEXT",
            "metodo_pagamento": "TEXT",
            "checklist": "TEXT",
            "dias_garantia": "INTEGER",
            "tipo_documento": "TEXT",
            "parcelas": "INTEGER",
            "detalhes_parcelas": "TEXT",
        }

        for col, tipo in obrig.items():
            if col not in cols:
                try:
                    if col == "dias_garantia":
                        default_val = "90"
                    elif col == "tipo_documento":
                        default_val = "'OS'"
                    elif col == "parcelas":
                        default_val = "1"
                    else:
                        default_val = "'Com Garantia'"

                    c.execute(
                        f"ALTER TABLE os ADD COLUMN {col} {tipo} DEFAULT {default_val}"
                    )
                    conn.commit()
                except sqlite3.Error as e:
                    print(f"Aviso: Não foi possível adicionar coluna {col}: {e}")
                    pass

        # Adicionar índices para melhor performance
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_numero ON os (numero)",
            "CREATE INDEX IF NOT EXISTS idx_cliente ON os (cliente)",
            "CREATE INDEX IF NOT EXISTS idx_modelo ON os (modelo)",
            "CREATE INDEX IF NOT EXISTS idx_imei ON os (imei)",
            "CREATE INDEX IF NOT EXISTS idx_problemas ON os (problemas)",
            "CREATE INDEX IF NOT EXISTS idx_tipo_documento ON os (tipo_documento)",
            "CREATE INDEX IF NOT EXISTS idx_situacao ON os (situacao)",
            "CREATE INDEX IF NOT EXISTS idx_entrada ON os (entrada)",
        ]
        for idx in indices:
            try:
                c.execute(idx)
                conn.commit()
            except sqlite3.Error as e:
                print(f"Aviso: Não foi possível criar índice: {e}")

        conn.close()
    except sqlite3.Error as e:
        messagebox.showerror(
            "Erro Crítico",
            f"Erro ao criar/acessar o banco de dados:\n{str(e)}\n\n"
            f"Verifique se você tem permissões de escrita no diretório:\n{APP_DIR}",
        )
        sys.exit(1)
    except Exception as e:
        messagebox.showerror(
            "Erro Crítico", f"Erro inesperado ao inicializar o banco de dados:\n{str(e)}"
        )
        sys.exit(1)


def _connect():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def get_next_document_number(tipo_documento):
    conn = sqlite3.connect(DB_NAME)
    try:
        c = conn.cursor()
        if tipo_documento == "OS":
            c.execute(
                "SELECT MAX(CAST(SUBSTR(numero, 4) AS INTEGER)) FROM os WHERE tipo_documento='OS'"
            )
            max_num = c.fetchone()[0] or 0
            return f"OS-{max_num+1:04d}"

        if tipo_documento == "VENDA":
            c.execute(
                "SELECT MAX(CAST(SUBSTR(numero, 7) AS INTEGER)) FROM os WHERE tipo_documento='VENDA'"
            )
            max_num = c.fetchone()[0] or 0
            return f"VENDA-{max_num+1:04d}"

        raise ValueError(f"Tipo de documento inválido: {tipo_documento}")
    finally:
        conn.close()


def insert_document(dados_db, caminho_pdf):
    conn = sqlite3.connect(DB_NAME)
    try:
        c = conn.cursor()

        cols = ", ".join(dados_db.keys())
        placeholders = ", ".join("?" * len(dados_db))
        values = tuple(dados_db.values()) + (caminho_pdf,)

        c.execute(f"INSERT INTO os ({cols}, arquivo) VALUES ({placeholders}, ?)", values)

        conn.commit()
    finally:
        conn.close()


def list_documents(search="", limit=50, offset=0):
    """Retorna (rows, total_records). rows é uma lista de dicts com as colunas do DB."""
    conn = _connect()
    try:
        c = conn.cursor()

        count_query = "SELECT COUNT(*) FROM os"
        count_params = []
        if search:
            search_pattern = f"%{search}%"
            count_query += (
                " WHERE numero LIKE ? OR cliente LIKE ? OR modelo LIKE ? OR imei LIKE ? OR problemas LIKE ?"
            )
            count_params = [search_pattern] * 5
        c.execute(count_query, count_params)
        total_records = c.fetchone()[0]

        query = "SELECT * FROM os"
        params = []
        if search:
            search_pattern = f"%{search}%"
            query += (
                " WHERE numero LIKE ? OR cliente LIKE ? OR modelo LIKE ? OR imei LIKE ? OR problemas LIKE ?"
            )
            params = [search_pattern] * 5
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        c.execute(query, params)
        rows = [dict(row) for row in c.fetchall()]
        return rows, total_records
    finally:
        conn.close()


def fetch_document(numero, tipo_documento):
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM os WHERE numero=? AND tipo_documento=?", (numero, tipo_documento)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_document(numero, tipo_documento, fields):
    """Atualiza colunas em `fields` para o registro (numero, tipo_documento)."""
    if not fields:
        return

    conn = sqlite3.connect(DB_NAME)
    try:
        set_clause = ", ".join(f"{col}=?" for col in fields.keys())
        params = list(fields.values()) + [numero, tipo_documento]
        conn.execute(
            f"UPDATE os SET {set_clause} WHERE numero=? AND tipo_documento=?", params
        )
        conn.commit()
    finally:
        conn.close()


def delete_document(numero, tipo_documento):
    conn = sqlite3.connect(DB_NAME)
    try:
        conn.execute(
            "DELETE FROM os WHERE numero=? AND tipo_documento=?", (numero, tipo_documento)
        )
        conn.commit()
    finally:
        conn.close()
