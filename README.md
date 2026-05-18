# NetHUB Ultimate v2.0

**Suite táctica de ciberseguridad y análisis de red con IA integrada**

NetHUB Ultimate es una aplicación de escritorio para Windows que combina herramientas de análisis de red, seguridad ofensiva, OSINT, monitoreo de sistemas y un asistente de inteligencia artificial local en una interfaz moderna y animada.

---

## Características principales

### 12 módulos integrados

| Módulo | Descripción |
|---|---|
| **Core Dashboard** | Panel central con 3 radares animados (SOC, LAN, Threat), monitoreo de recursos en tiempo real, noticias RSS de ciberseguridad y asesoría táctica con IA |
| **Ciber Ofensiva** | Escáner de puertos, generador de payloads inversos, interfaz gráfica para Nmap |
| **Reconocimiento de Señales** | Monitor de ping, consulta DNS, rastreo GeoIP, test de velocidad de banda ancha |
| **OSINT y DarkNet** | Geolocalización IP, enumerador de subdominios, rastreador de usernames |
| **Hex Code Sandbox** | Editor de código Python con ejecución, generación y explicación por IA |
| **Cifrado (Cipher Deck)** | Encriptación de texto (Base64, Caesar, Rot13), generador de hashes, cracker de hashes por diccionario |
| **Telemetría Kernel** | Gestor de procesos (con kill), analizador de disco |
| **Centinela en Vivo** | Gráficas en tiempo real de CPU/RAM/Disco, monitoreo de I/O de red |
| **Bóveda Segura** | Buscador de archivos, detector de duplicados, calculadora de hash, renombrador masivo |
| **Auxiliares de Diagnóstico** | Notas rápidas, temporizador de cuenta regresiva |
| **Notas** | Editor markdown completo con copiloto IA (autocompletar, corregir, reescribir, continuar), etiquetas, anclaje, búsqueda y exportación |
| **Caja de Arena** | Simulación de física de arena cayendo (140x80 grid con gravedad) |

### Asistente IA con Ollama

- Chat conversacional con respuestas en streaming
- Recomendaciones tácticas de ciberseguridad en el dashboard
- Generación y análisis de código
- Análisis profundo de CVEs
- Detección de phishing e ingeniería social
- Análisis de inteligencia de amenazas
- Resumización de noticias
- Copiloto para markdown

---

## Requisitos del sistema

- **Sistema operativo:** Windows 10/11
- **Python:** 3.10 o superior
- **RAM:** 4 GB mínimo (8 GB recomendado)
- **Disco:** 500 MB libres
- **Ollama:** Instalado y corriendo (opcional, para funciones de IA)

### Para funciones de IA:
- [Ollama](https://ollama.com/) instalado y ejecutando `ollama serve`
- Modelo `llama3:8b` descargado: `ollama pull llama3:8b`

---

## Instalación

### Opción A: Ejecutar desde código fuente

1. Clona o descarga el repositorio
2. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```
3. Ejecuta la aplicación:
   ```
   python main.py
   ```

### Opción B: Ejecutable precompilado

1. Descarga el instalador desde la fuente oficial
2. Ejecuta el instalador y sigue las instrucciones
3. Inicia NetHUB Ultimate desde el menú de inicio o acceso directo

> **Nota:** Para usar las funciones de IA, debes tener Ollama instalado y corriendo por separado.

---

## Primer uso

1. Al iniciar, verás la pantalla de carga con la animación Matrix
2. Crea una cuenta en la pestaña **Registro** o inicia sesión si ya tienes una
3. También puedes iniciar sesión con tu cuenta de Google (requiere configuración OAuth)
4. Una vez dentro, explora los módulos desde la barra lateral izquierda
5. Haz clic en el icono ⚡ para expandir/colapsar la barra lateral

---

## Configuración

### Temas de color
NetHUB incluye 4 temas incorporados:
- **Dark** (oscuro clásico)
- **Blood** (tonos rojos)
- **Matrix** (verde hacker)
- **Cyber** (púrpura neón)

También puedes crear un tema personalizado desde **Configuración > Personalizar colores**.

### Sonidos
Los efectos de sonido se pueden activar/desactivar desde **Configuración**.

### Ollama / IA
Si tienes Ollama instalado en una dirección diferente a `http://localhost:11434`, puedes cambiarla desde **Configuración > Ollama**.

---

## Estructura del proyecto

```
NETHUB/
├── main.py                 # Aplicacion principal (GUI)
├── core.py                 # Logica central (usuarios, config, GLI)
├── update_checker.py       # Sistema de actualizaciones
├── requirements.txt        # Dependencias de Python
├── version.json            # Version actual (para actualizaciones)
├── .gitignore              # Archivos ignorados por git
├── LICENCIA.txt            # Licencia comercial
├── README.md               # Este archivo
│
├── modules/                # Sistema de modulos
│   ├── base_module.py      # Clase base para modulos
│   ├── shared.py           # Componentes UI compartidos
│   ├── module_manager.py   # Gestor de modulos
│   ├── hacking_module.py   # Herramientas ofensivas
│   ├── network_module.py   # Reconocimiento de red
│   ├── osint_module.py     # OSINT
│   ├── code_module.py      # Sandbox de codigo
│   ├── crypto_module.py    # Cifrado
│   ├── system_module.py    # Telemetria del sistema
│   ├── monitor_module.py   # Monitoreo en vivo
│   ├── files_module.py     # Gestion de archivos
│   ├── utils_module.py     # Utilidades
│   ├── notas_module.py     # Editor de notas
│   ├── sandbox_module.py   # Simulacion de arena
│   └── custom/             # Modulos personalizados del usuario
│       └── ejemplo_module.py
│
├── build/                  # Compilacion
│   ├── compile.bat         # Compilar .exe (PyInstaller)
│   └── gen_release.py      # Generar version.json desde Python
│
├── release/                # Automatizacion de releases
│   ├── prepare.bat         # Flujo completo: compilar + preparar repos
│   └── publish.bat         # Publicar en GitHub (git push)
│
├── tests/                  # Pruebas unitarias
│   └── test_core.py
├── run_tests.bat           # Ejecutar tests
│
└── notes/                  # Notas markdown del usuario (no distribuir)
```

## Flujo de trabajo para releases

### Configuracion inicial (una sola vez)

1. Abre `release\prepare.bat` en un editor
2. Cambia `TU_USUARIO` por tu usuario real de GitHub
3. Configura los nombres de repos que prefieras

### Publicar una nueva version

Ejecuta:
```
release\prepare.bat
```

El script te pide:
- Numero de version (ej: 2.1.0)
- Si es obligatoria
- Lista de cambios (changelog)
- Mensaje corto

Luego automaticamente:
1. Genera `version.json` actualizado
2. Compila el `.exe`
3. Prepara el repo de codigo fuente (`../nethub-ultimate`)
4. Prepara el repo de distribucion (`../nethub-distro`)
5. Hace git commit en ambos

### Subir a GitHub

**Primera vez:**
```
cd ..\nethub-ultimate
git remote add origin https://github.com/TU_USUARIO/nethub-ultimate.git
git branch -M main
git push -u origin main

cd ..\nethub-distro
git remote add origin https://github.com/TU_USUARIO/nethub-distro.git
git branch -M main
git push -u origin main
```

**Actualizaciones siguientes:**
```
release\publish.bat
```

### Solo compilar el .exe

```
build\compile.bat
```
NETHUB/
├── main.py                 # Aplicación principal
├── requirements.txt        # Dependencias de Python
├── config.json             # Configuración de la app
├── users.json              # Base de datos de usuarios (local)
├── google_oauth_client.json # Credenciales OAuth de Google
├── modules/                # Sistema de módulos
│   ├── base_module.py      # Clase base para módulos
│   ├── shared.py           # Componentes UI compartidos
│   ├── hacking_module.py   # Herramientas ofensivas
│   ├── network_module.py   # Reconocimiento de red
│   ├── osint_module.py     # OSINT
│   ├── code_module.py      # Sandbox de código
│   ├── crypto_module.py    # Cifrado
│   ├── system_module.py    # Telemetría del sistema
│   ├── monitor_module.py   # Monitoreo en vivo
│   ├── files_module.py     # Gestión de archivos
│   ├── utils_module.py     # Utilidades
│   ├── notas_module.py     # Editor de notas
│   └── sandbox_module.py   # Simulación de arena
├── notes/                  # Directorio de notas markdown
├── build/                  # Scripts de compilación
│   └── build.bat           # Script de empaquetado
└── tests/                  # Pruebas unitarias
    └── test_core.py
```

---

## Seguridad

- Las contraseñas se almacenan con **bcrypt** (hash con salt y costo adaptativo)
- Las credenciales de OAuth de Google **NO** se distribuyen; cada distribuidor debe configurar las suyas
- Todos los datos se almacenan localmente
- No se envían datos a servidores externos (excepto consultas a Ollama local y feeds RSS públicos)

> **Advertencia:** Las herramientas de escaneo y análisis de red incluidas deben usarse únicamente en sistemas de tu propiedad o con autorización explícita del propietario. El uso no autorizado puede constituir un delito.

---

## Sistema de actualizaciones

NetHUB incluye un verificador de actualizaciones integrado que consulta un archivo `version.json` en GitHub (gratis, sin hosting).

Los usuarios reciben notificacion automatica al abrir la app cuando hay una version nueva. El sistema se configura automaticamente cuando usas `release\prepare.bat`, ya que genera el `version.json` con la URL correcta.

### Publicar una actualizacion

Simplemente ejecuta:
```
release\prepare.bat
```

Esto genera `version.json`, compila el `.exe`, y prepara ambos repos. Luego sube con `release\publish.bat` o haz `git push` manualmente.

---

## Compilar tu propio ejecutable

Si deseas generar un ejecutable:

```
pip install pyinstaller
pyinstaller --onefile --windowed --icon=assets/icon.ico --name "NetHUB_Ultimate" main.py
```

O usa el script incluido:
```
build\build.bat
```

---

## Licencia

NetHUB Ultimate es software propietario bajo **licencia comercial**. Todos los derechos reservados.

Consulta el archivo `LICENCIA.txt` para los términos completos.

El uso no autorizado, distribución o ingeniería inversa están estrictamente prohibidos.

---

## Créditos

Desarrollado con:
- **CustomTkinter** - Framework de interfaz gráfica
- **Ollama** - Motor de IA local
- **Matplotlib** - Gráficas en tiempo real
- **psutil** - Monitoreo del sistema

---

**NetHUB Ultimate v2.0** - 2026
"# nethub" 
