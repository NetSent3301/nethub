# 🏪 Setup del Marketplace de Plugins

## ¿Qué se instaló?

Se agregaron 3 componentes nuevos al proyecto:

### 1. **`src/core/marketplace.py`**
- Gestor central del marketplace
- Descarga catálogo desde GitHub
- Gestiona instalación/desinstalación de plugins
- Caché local automático

### 2. **`src/modules/marketplace_module.py`**
- Módulo UI visible en NetHUB
- Búsqueda de plugins
- Instalación/desinstalación
- Detalles de plugins

### 3. **Actualización de `src/modules/module_manager.py`**
- Agregado `marketplace_module` a la lista de módulos built-in

---

## ⚙️ Configuración Necesaria

### Opción A: Usar repositorio GitHub existente

Si ya tienes un repo en GitHub, solo necesitas:

1. **En tu repo**, crea la estructura:
   ```
   plugins/
   ├── catalog.json
   ├── ssl-analyzer/
   │   ├── plugin.json
   │   └── main.py
   └── api-scanner/
       ├── plugin.json
       └── main.py
   ```

2. **En `marketplace.py`**, línea ~21, actualiza:
   ```python
   GITHUB_REPO = "tunombre/tu-repo"  # Cambiar aquí
   ```

### Opción B: Crear nuevo repo solo para plugins

1. Crea en GitHub: `nethub-marketplace` (o similar)
2. Copia la estructura arriba
3. Usa ese repo en `marketplace.py`

---

## 📋 Estructura de catalog.json

```json
{
  "version": "1.0",
  "last_updated": "2026-05-24",
  "plugins": [
    {
      "id": "plugin-unique-id",
      "name": "Plugin Display Name",
      "version": "1.0.0",
      "author": "Tu Nombre",
      "description": "Descripción corta del plugin",
      "icon": "🎯",
      "category": "security|osint|utils|custom",
      "tags": ["tag1", "tag2", "tag3"],
      "min_nethub_version": "2.4",
      "license": "MIT",
      "repository": "https://github.com/user/repo",
      "download_url": "https://github.com/user/repo/archive/refs/heads/main.zip",
      "screenshots": [],
      "permissions": ["network", "file_access"],
      "dependencies": []
    }
  ]
}
```

---

## 📦 Estructura de un plugin en el marketplace

Cada carpeta `plugins/{plugin-id}/` debe contener:

### `plugin.json`
```json
{
  "id": "ssl-analyzer",
  "name": "SSL Certificate Analyzer",
  "version": "1.0.0",
  "author": "Tu Nombre",
  "description": "Análisis de certificados SSL/TLS",
  "icon": "🔐"
}
```

### `main.py`
```python
import customtkinter as ctk
from modules.base_module import BaseModule

class SSLAnalyzerModule(BaseModule):
    name = "SSL Analyzer"
    icon = "🔐"
    description = "Análisis de certificados SSL/TLS"

    def build(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            frame,
            text="Tu plugin aquí",
            font=("Arial", 14)
        ).pack()
```

---

## 🧪 Probar localmente (RECOMENDADO)

Antes de subir a GitHub, prueba el plugin localmente:

1. Crea la carpeta: `plugins/test-plugin/`
2. Agrega `plugin.json` y `main.py`
3. Reinicia NetHUB
4. El plugin debe aparecer en la barra lateral

**Una vez funcione**, súbelo a GitHub y agrega su entrada al `catalog.json`.

---

## 🚀 URLs de ejemplo para GitHub

Si tu repo es: `github.com/usuario/nethub-marketplace`

La rama es: `main`

Los URLs serían:

```
Catalog:  https://raw.githubusercontent.com/usuario/nethub-marketplace/main/catalog.json
Plugin:   https://github.com/usuario/nethub-marketplace/archive/refs/heads/main.zip
```

---

## 📝 Checklist de Setup

- [ ] Actualizar `GITHUB_REPO` en `src/core/marketplace.py`
- [ ] Crear repo en GitHub
- [ ] Crear estructura `/plugins/` en el repo
- [ ] Agregar `catalog.json` al repo
- [ ] Probar que NetHUB descarga el catálogo
- [ ] Crear primer plugin de ejemplo
- [ ] Probar instalación desde marketplace
- [ ] Documentar en README del proyecto

---

## 🔗 Variables a actualizar en `src/core/marketplace.py`

**Línea ~21:**
```python
GITHUB_REPO = "NetSent3301/nethub-marketplace"  # ← CAMBIAR AQUÍ
```

Eso es todo. El resto es automático.

---

## 💡 Tips

- El catálogo se **cachea localmente** para funcionar sin internet
- Los plugins se descargan como **ZIP desde GitHub**
- Valida que `plugin.json` esté en la raíz del ZIP
- Usa versionado semántico (v1.0.0, v1.1.0, etc)

¿Necesitas ayuda configurando el repo?
