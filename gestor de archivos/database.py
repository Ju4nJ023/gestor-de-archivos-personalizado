import sqlite3
import threading

# --- CONEXIÓN SINGLETON THREAD-SAFE ---
_lock = threading.Lock()
_connection = None

def _get_connection(db_name="gestor_archivos.db"):
    """Devuelve una conexión compartida thread-safe con WAL y timeout de 30s."""
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(db_name, timeout=30, check_same_thread=False)
        _connection.execute('PRAGMA journal_mode=WAL;')
        _connection.execute('PRAGMA busy_timeout=30000;')
    return _connection

def inicializar_db(db_name="gestor_archivos.db"):
    """
    Crea una base de datos SQLite y una tabla 'archivos' con las columnas
    especificadas. Asegura que 'ruta_completa' sea única.
    """
    conn = _get_connection(db_name)
    with _lock:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS archivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                ruta_completa TEXT NOT NULL UNIQUE,
                extension TEXT,
                tamaño_mb REAL,
                hash_id TEXT,
                contenido_texto TEXT
            )
        ''')
        
        try:
            cursor.execute("ALTER TABLE archivos ADD COLUMN contenido_texto TEXT")
        except sqlite3.OperationalError:
            pass

        conn.commit()
    
    print(f"Base de datos '{db_name}' inicializada con éxito.")

def indexar_archivo(datos, db_name="gestor_archivos.db"):
    """
    Inserta masivamente una lista de archivos en la base de datos usando executemany.
    Usamos REPLACE para que actualice los registros existentes.
    'datos' debe ser una lista de tuplas: (nombre, ruta_completa, extension, tamaño_mb, hash_id, contenido_texto)
    """
    conn = _get_connection(db_name)
    with _lock:
        cursor = conn.cursor()
        try:
            cursor.executemany('''
                INSERT OR REPLACE INTO archivos (nombre, ruta_completa, extension, tamaño_mb, hash_id, contenido_texto)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', datos)
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error al insertar masivamente: {e}")

def cerrar_conexion():
    """Cierra la conexión compartida. Llamar al finalizar el programa."""
    global _connection
    if _connection:
        try:
            _connection.close()
        except Exception:
            pass
        _connection = None

if __name__ == "__main__":
    inicializar_db()
