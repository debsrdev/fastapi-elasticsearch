# FastAPI + Elasticsearch (Lexical, Semantic y Hybrid Search)

Este proyecto implementa una API REST construida con FastAPI que permite realizar búsquedas sobre texto utilizando Elasticsearch. La aplicación combina tres enfoques distintos de búsqueda: léxica, semántica e híbrida, permitiendo comparar y entender cómo funcionan juntas en un mismo sistema.

El proyecto está pensado como una base educativa y demostrativa para entender la búsqueda moderna basada en texto y embeddings.

---

## Descripción general

La API permite almacenar frases junto con sus embeddings y metadatos, y posteriormente recuperarlas mediante distintos tipos de búsqueda.

Se soportan dos modos de generación de embeddings:

- Modo fake, para desarrollo y pruebas sin depender de servicios externos.
- Modo OpenAI, para obtener embeddings reales y realizar búsquedas semánticas de mayor calidad.

El motor de búsqueda utilizado es Elasticsearch, que actúa tanto como buscador textual tradicional como motor de búsqueda vectorial.

---

## Tipos de búsqueda soportados

### Búsqueda léxica

Se basa en la coincidencia de palabras dentro del texto utilizando el motor BM25 de Elasticsearch. Es útil cuando las palabras exactas de la consulta son importantes.

### Búsqueda semántica

Utiliza embeddings y búsqueda por similitud vectorial para encontrar textos relacionados por significado, aunque no compartan las mismas palabras.

### Búsqueda híbrida

Combina la búsqueda léxica y la búsqueda semántica en una sola consulta, permitiendo obtener resultados más equilibrados.

---

## Stack tecnológico

El proyecto utiliza las siguientes tecnologías:

- Python 3.10 o superior
- FastAPI como framework web
- Elasticsearch como motor de búsqueda
- Kibana para visualización de datos
- OpenAI Embeddings de forma opcional
- Docker y Docker Compose para el entorno local

---

## Estructura del proyecto

El proyecto se organiza en los siguientes archivos principales:

- main.py: contiene la API FastAPI y toda la lógica de búsqueda
- requirements.txt: dependencias del proyecto
- docker-compose.yaml: servicios de Elasticsearch y Kibana
- .env: variables de entorno
- venv: entorno virtual de Python

---

## Variables de entorno

El proyecto se configura mediante variables de entorno definidas en un archivo `.env`.

Variables principales:

- ELASTIC_URL: URL de conexión a Elasticsearch
- ELASTIC_INDEX: nombre del índice donde se almacenan los documentos
- EMBEDDING_PROVIDER: proveedor de embeddings, puede ser fake u openai
- EMBEDDING_DIM: dimensión del embedding
- OPENAI_API_KEY: clave de OpenAI (solo necesaria si se usa openai)
- OPENAI_EMBED_MODEL: modelo de embeddings de OpenAI

Notas importantes:

- Si se utiliza el modo fake, no es necesario configurar OpenAI.
- Si se utiliza OpenAI, la dimensión del embedding debe coincidir con la del modelo seleccionado.

---

## Arranque del entorno con Docker

El proyecto incluye un entorno Docker para ejecutar Elasticsearch y Kibana en local.

Al iniciar Docker Compose se levantan dos servicios:

- Elasticsearch, que actúa como motor de búsqueda
- Kibana, que permite inspeccionar índices y documentos

---

## Ejecución de la API

La API se ejecuta localmente mediante FastAPI.

Pasos generales:

- Activar el entorno virtual de Python
- Instalar las dependencias del proyecto
- Ejecutar la aplicación con un servidor ASGI

Una vez iniciada, la API queda disponible en el puerto configurado y expone documentación automática.

---

## Endpoints principales

### Health check

Permite comprobar que la API y la conexión con Elasticsearch funcionan correctamente.

### Ingesta de documentos

Permite insertar una o varias frases junto con metadatos. Cada frase se almacena como un documento con su embedding.

### Búsqueda léxica

Devuelve documentos basados en coincidencia textual.

### Búsqueda semántica

Devuelve documentos basados en similitud de embeddings.

### Búsqueda híbrida

Devuelve documentos combinando texto y embeddings.

### Actualización de documentos

Permite modificar el texto y los metadatos de un documento existente.

### Eliminación de documentos

Permite borrar documentos por su identificador.

---

## Visualización con Kibana

Kibana se utiliza para inspeccionar los documentos almacenados en Elasticsearch.

Permite:

- Ver documentos indexados
- Comprobar campos de texto, metadatos y embeddings
- Probar consultas manuales

Kibana no está pensado como visor de embeddings, sino como visor de documentos y resultados de búsqueda.

---

## Casos de uso

Este proyecto es útil para:

- Aprender cómo funciona la búsqueda semántica
- Comparar búsqueda léxica y vectorial
- Implementar sistemas RAG
- Crear buscadores inteligentes
- Experimentar con Elasticsearch como motor híbrido
- Comparar Elasticsearch con bases de datos vectoriales puras

---

## Notas finales

Elasticsearch permite combinar búsqueda tradicional y búsqueda vectorial en un único motor. Esto lo convierte en una solución muy potente cuando el texto sigue siendo una parte clave del sistema.

Este proyecto sirve como base para entender y experimentar con este tipo de arquitectura.
