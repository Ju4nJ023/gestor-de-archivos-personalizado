"""
Script de limpieza puntual: reprocesa duplicados y archivos sueltos.
Usa las funciones integradas de indexador.py con conexión thread-safe.
"""
import database
import indexador

DB_NAME = "gestor_archivos.db"

# Paso 1: Limpiar la base de datos
conn = database._get_connection(DB_NAME)
try:
    with database._lock:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM archivos')
        conn.commit()
    print("Base de datos limpiada.")
finally:
    database.cerrar_conexion()

# Paso 2: Ejecutar limpieza de archivos sueltos y duplicados
indexador.cleanup_loose_files()

# Paso 3: Re-indexar todo desde cero
indexador.index_new_files()

# Paso 4: Cerrar limpiamente
database.cerrar_conexion()
print("Limpieza completada.")
