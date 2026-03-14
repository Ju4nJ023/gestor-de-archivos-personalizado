import os

file_path = "app_moderna.py"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Buscamos el bloque de botones desde btn_expedientes hasta self.btn_actualizar
import re

pattern = r'(\s*btn_expedientes = .*?)(?=\s*# Botón actualizar abajo del todo)'

new_buttons = """        btn_expedientes = ctk.CTkButton(self.sidebar_frame, text="💼 Despacho: M. del Pilar", command=lambda: self.cargar_categoria("💼 Despacho: María del Pilar Fernández", ["%Despacho María del Pilar Fernández%"], "path"), **btn_estilo)
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
        btn_papeles.grid(row=6, column=0, pady=5, sticky="ew")
"""

new_content = re.sub(pattern, new_buttons, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("UI Replaced")
