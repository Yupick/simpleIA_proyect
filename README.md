LLM Project

Este es un sistema LLM modular construido con FastAPI, Transformers y otras tecnologías.

Estructura del Proyecto:
- config: Contiene el archivo de configuración (config.json).
- app: Código Python de la aplicación (API, clientes web y de línea de comandos, trainer).
- trainer_llm: Archivos para entrenamiento (subcarpetas dialogue y knowledge).
- model_llm: Carpeta donde se guardan los modelos entrenados.
- templates: Plantillas HTML para la interfaz web.
- feedback: Base de datos SQLite para feedback y usuarios.
- static: Archivos estáticos (CSS, JavaScript, etc.).
- test: Scripts y archivos para testing.
- requirements.txt: Dependencias de Python.
- run_llm.sh: Script para iniciar la aplicación.
- setup_env.sh: Script para crear la estructura de directorios.

Instrucciones:
1. Ejecuta setup_env.sh para crear las carpetas necesarias.
2. Instala las dependencias con: pip install -r requirements.txt
3. Inicia la API y el cliente web según sea necesario.
