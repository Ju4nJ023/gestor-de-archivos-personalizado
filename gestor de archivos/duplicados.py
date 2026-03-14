import sqlite3
import json
import time
import os

DB_NAME = "gestor_archivos.db"
REPORT_FILE = "reporte_duplicados.json"

def find_duplicates():
    """Identifica archivos duplicados basados en su hash MD5 y genera un reporte JSON."""
    if not os.path.exists(DB_NAME):
        print(f"Error: La base de datos '{DB_NAME}' no existe. Por favor, ejecuta el indexador primero.")
        return

    print("Analizando la base de datos en busca de duplicados...")
    start_time = time.time()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Encontrar hashes con más de un archivo
    cursor.execute('''
        SELECT hash_id, COUNT(id) as count, MAX(tamaño_mb) as max_size_mb 
        FROM archivos 
        WHERE hash_id IS NOT NULL 
        GROUP BY hash_id 
        HAVING COUNT(id) > 1 
        ORDER BY count DESC, max_size_mb DESC
    ''')
    
    duplicates_groups = cursor.fetchall()
    
    report_data = {
        "metadata": {
            "total_duplicate_groups": len(duplicates_groups),
            "total_recoverable_mb": 0.0
        },
        "duplicates": []
    }
    
    total_recoverable_space_mb = 0
    
    for hash_id, count, max_size_mb in duplicates_groups:
        cursor.execute('SELECT id, ruta_completa, nombre, tamaño_mb FROM archivos WHERE hash_id = ?', (hash_id,))
        files_in_group = cursor.fetchall()
        
        if not files_in_group:
            continue
            
        # El espacio recuperable es el tamaño del archivo multiplicado por (copias - 1)
        # Asumiendo que dejamos 1 copia original. Tomamos el tamaño_mb del primer elemento por seguridad.
        size_mb = files_in_group[0][3] or 0
        recoverable_space_mb = size_mb * (count - 1)
        total_recoverable_space_mb += recoverable_space_mb
        
        group_info = {
            "hash_id": hash_id,
            "file_size_mb": size_mb,
            "recoverable_mb": recoverable_space_mb,
            "copies_count": count,
            "files": [
                {
                    "id": f_id,
                    "path": f_path,
                    "name": f_name
                } for f_id, f_path, f_name, _ in files_in_group
            ]
        }
        
        report_data["duplicates"].append(group_info)
        
    conn.close()
    
    # Actualizar metadatos del reporte con los totales
    report_data["metadata"]["total_recoverable_mb"] = round(total_recoverable_space_mb, 2)
    
    # Guardar en JSON
    with open(REPORT_FILE, 'w', encoding='utf-8') as json_file:
        json.dump(report_data, json_file, indent=4, ensure_ascii=False)
        
    end_time = time.time()
    
    print(f"Análisis completado en {end_time - start_time:.2f} segundos.")
    print(f"Se encontraron {len(duplicates_groups)} grupos de archivos duplicados.")
    print(f"Espacio total que se podría recuperar: {report_data['metadata']['total_recoverable_mb']} MB")
    print(f"Reporte generado exitosamente en: {os.path.abspath(REPORT_FILE)}")

if __name__ == "__main__":
    find_duplicates()
