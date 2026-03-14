import customtkinter as ctk
import sqlite3
import os
import threading
from tkinter import messagebox
import time
import indexador
import database
import unicodedata

def safe_exists(path):
    try:
        if not path: return False
        os.stat(path)
        return True
    except OSError:
        return False


# Configuración de apariencia
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

DB_NAME = "gestor_archivos.db"

class AppLimpiaPC(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Mi Asistente Personal")
        self.geometry("1050x700")
        
        # Grid layout: 1 row, 2 columns (Sidebar and Main Area)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=260) # Sidebar fija
        self.grid_columnconfigure(1, weight=1) # Main area expands
        
        self.crear_sidebar()
        self.crear_area_principal()
        
        # Timer para el debounce del buscador
        self.search_after_id = None
        
        self.popup_duplicados = None
        self.scroll_duplicados = None
        self.vars_seleccion_duplicados = []
        
        # --- Automatización (Escaneo Silencioso y Vigilante) ---
        indexador.on_file_moved_callback = self.lanzar_toast
        indexador.on_file_needs_manual_classification = self.mostrar_popup_clasificacion
        indexador.on_duplicate_found_callback = self.mostrar_popup_duplicado
        indexador.on_duplicate_deleted_callback = self.mostrar_toast_eliminado
        indexador.on_reading_started_callback = self.mostrar_leyendo
        indexador.on_reading_finished_callback = self.ocultar_leyendo
        threading.Thread(target=indexador.start_watchdog, daemon=True).start()
        threading.Thread(target=indexador.index_new_files, daemon=True).start()
        threading.Thread(target=indexador.cleanup_loose_files, daemon=True).start()
        
        # Cargar vista vacía o inicio
        self.mostrar_inicio()

    def crear_sidebar(self):
        # Sidebar con color más oscuro #333333 (modo oscuro)
        self.sidebar_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray85", "#333333"))
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1) # Empuja hacia abajo el botón de actualizar
        
        lbl_titulo = ctk.CTkLabel(self.sidebar_frame, text="Mi Asistente\nPersonal", font=("Segoe UI", 24, "bold"))
        lbl_titulo.grid(row=0, column=0, padx=20, pady=(40, 40))
        
        # Opciones de la botonera lateral (sin transparencias, con hover diferente para iluminar)
        btn_estilo = {
            "height": 55, 
            "anchor": "w", 
            "font": ("Segoe UI", 16, "bold"), 
            "fg_color": ("gray85", "#333333"), 
            "text_color": ("black", "white"), 
            "hover_color": ("#d0d0d0", "#444444"),
            "corner_radius": 0 # Bordes rectos para ocupar todo el ancho visualmente
        }
        
        btn_expedientes = ctk.CTkButton(self.sidebar_frame, text="💼 Despacho: M. del Pilar", command=lambda: self.cargar_categoria("💼 Despacho: María del Pilar Fernández", ["%Despacho María del Pilar Fernández%"], "path"), **btn_estilo)
        btn_expedientes.grid(row=1, column=0, pady=2, sticky="ew")
        
        btn_juanjose = ctk.CTkButton(self.sidebar_frame, text="👤 Carpeta: Juan José", command=lambda: self.cargar_categoria("👤 Carpeta: Juan José", ["%Juan_Jose%"], "path"), **btn_estilo)
        btn_juanjose.grid(row=2, column=0, pady=2, sticky="ew")
        
        btn_juandiego = ctk.CTkButton(self.sidebar_frame, text="👤 Carpeta: Juan Diego", command=lambda: self.cargar_categoria("👤 Carpeta: Juan Diego", ["%Juan_Diego%"], "path"), **btn_estilo)
        btn_juandiego.grid(row=3, column=0, pady=2, sticky="ew")
        
        btn_oscar = ctk.CTkButton(self.sidebar_frame, text="👤 Carpeta: Oscar", command=lambda: self.cargar_categoria("👤 Carpeta: Oscar", ["%Oscar%"], "path"), **btn_estilo)
        btn_oscar.grid(row=4, column=0, pady=2, sticky="ew")
        
        btn_hogar = ctk.CTkButton(self.sidebar_frame, text="🏠 Gastos del Hogar", command=lambda: self.cargar_categoria("🏠 Gastos del Hogar", ["%Gastos_Hogar%"], "path"), **btn_estilo)
        btn_hogar.grid(row=5, column=0, pady=2, sticky="ew")
        
        btn_papeles = ctk.CTkButton(self.sidebar_frame, text="📄 Todos mis Papeles", command=lambda: self.cargar_categoria("Todos mis Papeles", [".pdf", ".docx", ".txt", ".doc"], "ext"), **btn_estilo)
        btn_papeles.grid(row=6, column=0, pady=2, sticky="ew")

        btn_revisar = ctk.CTkButton(self.sidebar_frame, text="❓ Por Revisar", command=lambda: self.cargar_categoria("❓ Por Revisar", ["%Por_Revisar%"], "path"), **btn_estilo)
        btn_revisar.grid(row=7, column=0, pady=5, sticky="ew")

        
        # Botón actualizar abajo del todo
        self.btn_actualizar = ctk.CTkButton(
            self.sidebar_frame, text="🔄 Actualizar archivos", height=50, 
            fg_color="#17a2b8", hover_color="#138496", font=("Segoe UI", 14, "bold"), 
            corner_radius=25, command=self.actualizar_indice
        )
        self.btn_actualizar.grid(row=8, column=0, padx=20, pady=(20, 10), sticky="ew")

        # Etiqueta de estado en la parte inferior (Leyendo archivo...)
        self.lbl_estado_lectura = ctk.CTkLabel(self.sidebar_frame, text="", text_color="#ffcc00", font=("Segoe UI", 12, "bold"))
        self.lbl_estado_lectura.grid(row=9, column=0, pady=(0, 20))

    def crear_area_principal(self):
        # Fondo principal en modo oscuro #2b2b2b
        self.main_frame = ctk.CTkFrame(self, fg_color=("#f0f0f0", "#2b2b2b"), corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=40)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Buscador superior redondeado que ocupa casi todo el ancho
        self.entry_buscar = ctk.CTkEntry(
            self.main_frame, 
            placeholder_text="🔎 Busca cualquier archivo, documento, palabra...",
            height=60,
            font=("Segoe UI", 20),
            corner_radius=30
        )
        self.entry_buscar.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.entry_buscar.bind("<KeyRelease>", self.on_search_type)
        
        # Título dinámico
        self.lbl_main_titulo = ctk.CTkLabel(self.main_frame, text="Búsqueda Global", font=("Segoe UI", 26, "bold"))
        self.lbl_main_titulo.grid(row=1, column=0, sticky="w", pady=(10, 20))
        
        # Panel scrollable de resultados
        self.panel_resultados = ctk.CTkScrollableFrame(self.main_frame, corner_radius=15, fg_color=("#f0f0f0", "#2b2b2b"))
        self.panel_resultados.grid(row=2, column=0, sticky="nsew")

    def lanzar_toast(self, mensaje):
        """Prepara el aviso para mostrarse de forma segura en el hilo de la interfaz sin superponerse."""
        self.after(0, lambda: self._mostrar_toast_real(mensaje))
        
    def _mostrar_toast_real(self, mensaje):
        """Muestra una etiqueta temporal verde en la esquina inferior derecha."""
        # Si ya hay un toast activo, lo destruimos primero
        if hasattr(self, 'current_toast') and self.current_toast is not None:
             try: self.current_toast.destroy()
             except: pass

        self.current_toast = ctk.CTkLabel(
            self, text=mensaje, fg_color="#28a745", text_color="white", corner_radius=10, 
            font=("Segoe UI", 16, "bold"), padx=20, pady=15
        )
        self.current_toast.place(relx=0.95, rely=0.95, anchor="se")
        
        # Ocultar mágicamente después de 4 segundos
        def destruir_toast(toast_ref):
            try: toast_ref.destroy()
            except: pass
            
        self.after(4000, lambda: destruir_toast(self.current_toast))
        
        # Auto-refrescar la vista actual si existe
        if hasattr(self, 'current_cat_args') and self.current_cat_args:
            # Dar un breve margen de 700ms para que sqlite haga el commit en indexador.py
            self.after(700, lambda: self.cargar_categoria(*self.current_cat_args))

    def mostrar_toast_eliminado(self, nombre):
        mensaje = f"Se ha detectado un duplicado de {nombre} y se ha eliminado para ahorrar espacio."
        self.after(0, lambda: self._mostrar_toast_real(mensaje))

    def mostrar_leyendo(self, nombre):
        texto_corto = nombre if len(nombre) <= 20 else nombre[:20] + "..."
        self.after(0, lambda: self.lbl_estado_lectura.configure(text=f"⏳ Leyendo: {texto_corto}"))
        
    def ocultar_leyendo(self):
        self.after(0, lambda: self.lbl_estado_lectura.configure(text=""))

    def actualizar_indice(self):
        """Lanza el Indexador."""
        self.btn_actualizar.configure(text="⏳ Buscando...", state="disabled", fg_color="gray")
        
        def run_index():
            try:
                indexador.index_new_files() 
            except Exception as e:
                print(e)
            
            if hasattr(self, 'btn_actualizar') and self.btn_actualizar.winfo_exists():
                self.btn_actualizar.configure(text="✅ Listo", state="normal", fg_color="#28a745")
                time.sleep(3)
                if self.btn_actualizar.winfo_exists():
                    self.btn_actualizar.configure(text="🔄 Actualizar archivos nuevos", fg_color="#17a2b8")
            
        threading.Thread(target=run_index, daemon=True).start()

    def mostrar_inicio(self):
        # Limpiar panel
        for w in self.panel_resultados.winfo_children(): w.destroy()
        self.lbl_main_titulo.configure(text="Bienvenido a tu Asistente")
        
        lbl = ctk.CTkLabel(self.panel_resultados, text="Empieza a escribir arriba para buscar en todo tu PC,\no selecciona una de las categorías a la izquierda.", font=("Segoe UI", 18), text_color="gray")
        lbl.pack(pady=40)

    def on_search_type(self, event):
        if self.search_after_id:
            self.after_cancel(self.search_after_id)
        # Esperar 250ms para que la búsqueda sea suave y sin sobrecargar la PC
        self.search_after_id = self.after(250, self.ejecutar_busqueda_global)
        
    def ejecutar_busqueda_global(self):
        termino = self.entry_buscar.get().strip()
        if not termino:
            self.mostrar_inicio()
            return
            
        self.lbl_main_titulo.configure(text=f"Resultados para '{termino}'")
        
        termino_norm = unicodedata.normalize('NFKD', termino).encode('ASCII', 'ignore').decode('utf-8').lower()
        partes = termino_norm.split()
        
        self.mostrar_mensaje_panel("Buscando...")

        def fetch_search():
            try:
                conn = database._get_connection(DB_NAME)
                cursor = conn.cursor()
                
                cursor.execute("PRAGMA table_info(archivos)")
                has_content = 'contenido_texto' in [c[1] for c in cursor.fetchall()]
                
                # Buscar cada palabra INDEPENDIENTEMENTE dentro de nombre O contenido
                condiciones = []
                params = []
                
                if has_content:
                    for p in partes:
                        condiciones.append("(lower(nombre) LIKE ? OR contenido_texto LIKE ?)")
                        params.extend([f"%{p}%", f"%{p}%"])
                else:
                    for p in partes:
                        condiciones.append("(lower(nombre) LIKE ?)")
                        params.extend([f"%{p}%"])
                        
                where_clause = " AND ".join(condiciones) if condiciones else "1=1"
                
                query = f"""
                    SELECT nombre, ruta_completa, tamaño_mb, {'contenido_texto' if has_content else "''"},
                           (SELECT COUNT(*) FROM archivos a2 WHERE a2.hash_id = archivos.hash_id AND a2.hash_id IS NOT NULL) as dup_count
                    FROM archivos 
                    WHERE {where_clause}
                    LIMIT 50
                """
                
                with database._lock:
                    cursor.execute(query, params)
                    resultados = cursor.fetchall()
                
                self.after(0, lambda: self.renderizar_tarjetas(resultados, termino_norm=termino_norm))
                
            except Exception as e:
                self.after(0, lambda e=e: self.mostrar_mensaje_panel(f"Error en búsqueda: {e}"))

        threading.Thread(target=fetch_search, daemon=True).start()

    def cargar_categoria(self, nombre_cat, filtros, tipo):
        self.current_cat_args = (nombre_cat, filtros, tipo)
        self.entry_buscar.delete(0, 'end') # Limpiar buscador del menú global
        self.lbl_main_titulo.configure(text=f"📂 {nombre_cat}")
        
        if not os.path.exists(DB_NAME):
            self.mostrar_mensaje_panel("Todavía se está preparando el sistema de archivos. Por favor espera.")
            return

        self.mostrar_mensaje_panel("Cargando categoría...")

        def fetch_data():
            try:
                conn = database._get_connection(DB_NAME)
                cursor = conn.cursor()
                
                condiciones = ""
                params = []
                if tipo == "ext":
                    placeholders = ",".join("?" * len(filtros))
                    condiciones = f"lower(extension) IN ({placeholders})"
                    params = [f.lower() for f in filtros]
                elif tipo == "path":
                    cond_list = []
                    params = []
                    for f in filtros:
                        f_safe = f.replace('/', '\\') 
                        f_safe_alt = f.replace('\\', '/')
                        cond_list.append("(lower(ruta_completa) LIKE ? OR lower(ruta_completa) LIKE ? OR lower(ruta_completa) LIKE ?)")
                        params.extend([f_safe.lower(), f_safe_alt.lower(), f.lower()])
                    condiciones = " OR ".join(cond_list)
                else:
                    condiciones = " OR ".join(cond_list)
                    params = [f.lower() for f in filtros]
                    
                query = f"""
                    SELECT nombre, ruta_completa, tamaño_mb, '', 
                           (SELECT COUNT(*) FROM archivos a2 WHERE a2.hash_id = archivos.hash_id AND a2.hash_id IS NOT NULL) as dup_count
                    FROM archivos WHERE {condiciones} LIMIT 60
                """
                
                with database._lock:
                    cursor.execute(query, params)
                    resultados = cursor.fetchall()
                
                self.after(0, lambda: self.renderizar_tarjetas(resultados))
                
            except sqlite3.Error as e:
                self.after(0, lambda e=e: self.mostrar_mensaje_panel(f"Error al cargar categoría: {e}"))

        threading.Thread(target=fetch_data, daemon=True).start()

    def mostrar_mensaje_panel(self, texto):
        for w in self.panel_resultados.winfo_children(): w.destroy()
        lbl = ctk.CTkLabel(self.panel_resultados, text=texto, font=("Segoe UI", 16))
        lbl.pack(pady=40)

    def renderizar_tarjetas(self, resultados, termino_norm=None):
        for w in self.panel_resultados.winfo_children(): w.destroy()
        
        if not resultados:
            self.mostrar_mensaje_panel("No se encontraron resultados.")
            return
            
        for nombre_ar, ruta, mb, txt, dup_count in resultados:
            # En lugar de usar "transparent", usamos el mismo color del panel para que se mezcle
            border_color = ("white", "#3a3a3a")
            border_width = 0
            
            es_duplicado = dup_count and dup_count > 1
            es_pesado = mb and mb > 500
            
            # Semáforo: Rojo si >500MB, Amarillo si duplicado. Solo prevalece Rojo.
            if es_pesado:
                border_color = "#dc3545" # Rojo
                border_width = 2
            elif es_duplicado:
                border_color = "#ffc107" # Amarillo
                border_width = 2
                
            tarjeta = ctk.CTkFrame(
                self.panel_resultados, 
                fg_color=("white", "#3a3a3a"), # Fondo tarjeta más claro que el #2b2b2b principal
                corner_radius=15, 
                border_color=border_color, 
                border_width=border_width
            )
            tarjeta.pack(fill="x", pady=8, padx=5)
            
            # Quitando el fg_color="transparent" que daba error, usamos el mismo que la `tarjeta`
            info_frame = ctk.CTkFrame(tarjeta, fg_color=("white", "#3a3a3a"))
            info_frame.pack(side="left", padx=20, pady=15, fill="both", expand=True)
            
            texto_mostrar = f"{nombre_ar} ({mb:.1f} MB)"
            
            # Etiquetas adicionales visuales para estilo semáforo
            if es_pesado: texto_mostrar += " 🔴 (Archivo Pesado)"
            if es_duplicado: texto_mostrar += " 🟡 (Copia Duplicada)"
                
            if txt and termino_norm:
                nombre_norm = unicodedata.normalize('NFKD', nombre_ar).encode('ASCII', 'ignore').decode('utf-8').lower()
                partes = termino_norm.split()
                en_nombre = all(p in nombre_norm for p in partes)
                if not en_nombre and all(p in txt for p in partes):
                    texto_mostrar += "\n💡 Encontrado dentro del documento"
                    
            lbl_text = ctk.CTkLabel(info_frame, text=texto_mostrar, font=("Segoe UI", 16, "bold"), justify="left")
            lbl_text.pack(anchor="w")
            
            lbl_ruta = ctk.CTkLabel(info_frame, text=ruta, font=("Segoe UI", 12), text_color="gray")
            lbl_ruta.pack(anchor="w", pady=(2, 0))
            
            btn_abrir = ctk.CTkButton(
                tarjeta, text="Abrir Archivo", fg_color="#0052cc", hover_color="#0041a3", font=("Segoe UI", 14, "bold"), width=120, height=40, corner_radius=15,
                command=lambda r=ruta: os.startfile(r) if safe_exists(r) else messagebox.showerror("Error", "El archivo fue movido, borrado o está solo en la nube.")
            )
            btn_abrir.pack(side="right", padx=20, pady=15)

    def mostrar_popup_duplicado(self, file_path, duplicate_path):
        """Muestra una única ventana permanente y añade el duplicado a la lista en tiempo real."""
        self.after(0, lambda: self._agregar_duplicado_ui(file_path, duplicate_path))

    def _agregar_duplicado_ui(self, arch_origen, arch_destino):
        # Crear la ventana si no existe o ha sido cerrada
        if self.popup_duplicados is None or not self.popup_duplicados.winfo_exists():
            self._crear_ventana_duplicados()
            
        nombre = os.path.basename(arch_origen)
        var = ctk.BooleanVar(value=True) 
        self.vars_seleccion_duplicados.append((var, arch_origen, arch_destino))
        
        frame_item = ctk.CTkFrame(self.scroll_duplicados, fg_color=("gray85", "#333333"))
        frame_item.pack(fill="x", pady=2)
        
        chk = ctk.CTkCheckBox(frame_item, text="", variable=var, width=20)
        chk.pack(side="left", padx=10, pady=5)
        
        lbl_n = ctk.CTkLabel(frame_item, text=nombre, font=("Segoe UI", 14, "bold"))
        lbl_n.pack(side="left", padx=5)
        
        # mostrar carpeta destino 
        dir_destino = os.path.basename(os.path.dirname(arch_destino))
        lbl_r = ctk.CTkLabel(frame_item, text=f"-> {dir_destino}", font=("Segoe UI", 12), text_color="gray")
        lbl_r.pack(side="right", padx=10)
        
        # Actualizar cantidad
        self.lbl_duplicados_titulo.configure(text=f"Archivos duplicados esperando revisión: {len(self.vars_seleccion_duplicados)}")

    def _crear_ventana_duplicados(self):
        self.popup_duplicados = ctk.CTkToplevel(self)
        self.popup_duplicados.title("Gestor Constante de Duplicados")
        self.popup_duplicados.geometry("650x500")
        self.popup_duplicados.attributes("-topmost", True)
        # IMPORTANTE: NO usamos grab_set() para que no bloquee y pueda actualizarse sola
        
        self.lbl_duplicados_titulo = ctk.CTkLabel(self.popup_duplicados, text="Archivos duplicados esperando revisión: 0", font=("Segoe UI", 16, "bold"))
        self.lbl_duplicados_titulo.pack(pady=15)
        
        self.scroll_duplicados = ctk.CTkScrollableFrame(self.popup_duplicados, fg_color="transparent")
        self.scroll_duplicados.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.vars_seleccion_duplicados = []
        
        def procesar():
            import shutil
            reemplazados = 0
            for var, arch_origen, arch_destino in self.vars_seleccion_duplicados:
                if var.get() and safe_exists(arch_origen):
                    try:
                        if safe_exists(arch_destino):
                            os.remove(arch_destino)
                        shutil.move(arch_origen, arch_destino)
                        reemplazados += 1
                    except Exception as e:
                        print(f"Error reemplazando: {e}")
            if reemplazados > 0:
                self.lanzar_toast(f"{reemplazados} archivos reemplazados con éxito.")
            self.vars_seleccion_duplicados.clear()
            self.popup_duplicados.destroy()
            
        def ignorar_todos():
            self.vars_seleccion_duplicados.clear()
            self.popup_duplicados.destroy()
            
        btn_frame = ctk.CTkFrame(self.popup_duplicados, fg_color="transparent")
        btn_frame.pack(pady=15, fill="x", padx=20)
        
        btn_style = {"height": 40, "font": ("Segoe UI", 14, "bold"), "corner_radius": 8}
        ctk.CTkButton(btn_frame, text="✅ Reemplazar Seleccionados", command=procesar, fg_color="#0052cc", hover_color="#0041a3", **btn_style).pack(side="left", padx=10, expand=True)
        ctk.CTkButton(btn_frame, text="✖️ Ignorar Todos", command=ignorar_todos, fg_color="gray", hover_color="#555555", **btn_style).pack(side="right", padx=10, expand=True)

        def on_close():
            self.vars_seleccion_duplicados.clear()
            self.popup_duplicados.destroy()
        self.popup_duplicados.protocol("WM_DELETE_WINDOW", on_close)

    def mostrar_popup_clasificacion(self, file_path):
        """Abre un popup para clasificar manualmente usando threading para no bloquear."""
        self.after(0, lambda: self._popup_clasificacion_ui(file_path))
        
    def _popup_clasificacion_ui(self, file_path):
        nombre = os.path.basename(file_path)
        
        popup = ctk.CTkToplevel(self)
        popup.title("Clasificación Manual Requerida")
        popup.geometry("500x400")
        popup.attributes("-topmost", True)
        popup.grab_set() 
        
        lbl = ctk.CTkLabel(popup, text=f"Archivo ambiguo detectado:\n'{nombre}'\n\n¿A qué carpeta pertenece?", font=("Segoe UI", 16, "bold"), justify="center")
        lbl.pack(pady=20)
        
        def mover_y_cerrar(destino_base, subcarpeta):
            import shutil, datetime
            import indexador # Assuming indexador module is available and contains get_documents_path
                
            base = os.path.join(indexador.get_documents_path(), destino_base)
            fecha = datetime.datetime.now().strftime("%Y-%m-%d")
            final_path = os.path.join(base, subcarpeta, fecha) if subcarpeta else os.path.join(base, fecha)
            
            def do_move():
                try:
                    os.makedirs(final_path, exist_ok=True)
                    import re
                    
                    base_name, _ext = os.path.splitext(nombre)
                    base_name_clean = re.sub(r'\s*(\(\d+\)|-\s*copia|-\d+)$', '', base_name, flags=re.IGNORECASE).strip()
                    clean_name = base_name_clean + _ext
                    nueva_ruta = os.path.join(final_path, clean_name)
                    
                    if safe_exists(nueva_ruta):
                        try:
                            is_same_size = (os.path.getsize(file_path) == os.path.getsize(nueva_ruta))
                        except OSError:
                            is_same_size = False
                        
                        if is_same_size:
                            # Eliminación idéntica
                            try:
                                os.remove(file_path)
                                self.mostrar_toast_eliminado(clean_name)
                            except: pass
                        else:
                            # Cambio de versión
                            self.mostrar_popup_duplicado(file_path, nueva_ruta)
                    else:
                        import shutil
                        shutil.move(file_path, nueva_ruta)
                        self.lanzar_toast(f"Clasificado en {destino_base}")
                except Exception as e:
                    print(f"Error moviendo archivo: {e}")
                    # Mostramos mensaje si Windows o Word lo tienen bloqueado
                    self.after(0, lambda err=e: messagebox.showerror("Error al mover", f"No se pudo mover el archivo. Puede que esté abierto en otro programa.\n\nDetalle: {err}"))
                    
            threading.Thread(target=do_move, daemon=True).start()
            popup.destroy()

        btn_style = {"height": 40, "font": ("Segoe UI", 14, "bold"), "corner_radius": 8}
        
        ctk.CTkButton(popup, text="💼 Despacho: M. del Pilar", command=lambda: mover_y_cerrar("Despacho María del Pilar Fernández", "General"), fg_color="#4b2e83", hover_color="#361f62", **btn_style).pack(pady=5, fill="x", padx=40)
        ctk.CTkButton(popup, text="👤 Juan José", command=lambda: mover_y_cerrar("Juan_Jose", ""), fg_color="#005b96", hover_color="#003f6b", **btn_style).pack(pady=5, fill="x", padx=40)
        ctk.CTkButton(popup, text="👤 Juan Diego", command=lambda: mover_y_cerrar("Juan_Diego", ""), fg_color="#b85042", hover_color="#8c392f", **btn_style).pack(pady=5, fill="x", padx=40)
        ctk.CTkButton(popup, text="👤 Oscar", command=lambda: mover_y_cerrar("Oscar", ""), fg_color="#d4af37", hover_color="#b5952f", **btn_style).pack(pady=5, fill="x", padx=40)
        ctk.CTkButton(popup, text="🏠 Gastos del Hogar", command=lambda: mover_y_cerrar("Gastos_Hogar", ""), fg_color="#28a745", hover_color="#1e7e34", **btn_style).pack(pady=5, fill="x", padx=40)
        ctk.CTkButton(popup, text="✖️ Ignorar", command=popup.destroy, fg_color="gray", hover_color="#555555", **btn_style).pack(pady=15, fill="x", padx=80)

if __name__ == "__main__":
    app = AppLimpiaPC()
    app.mainloop()
