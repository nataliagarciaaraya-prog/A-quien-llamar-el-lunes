# Versu AI
# Limpieza y validación de datos de uso mensual

Módulo en Python para la **limpieza, validación y preparación de datos mensuales de uso de clientes** a partir del archivo `uso_mensual.csv`.

El programa valida tanto la estructura del archivo como los datos de cada fila, identifica registros inválidos, registra los motivos de descarte y genera avisos para datos faltantes que no necesariamente invalidan la fila.

---

## 📁 Estructura esperada

El proyecto utiliza principalmente los siguientes archivos:

```text
.
├── limpieza_datos.py
├── uso_mensual.csv
├── uso_mensual_limpio.csv
├── uso_mensual_log_descartes.csv
└── uso_mensual_avisos.csv
```
Archivos de entrada
uso_mensual.csv

Archivo con los datos mensuales de uso de la plataforma.

El programa espera un conjunto específico de columnas y valida que no falten columnas ni existan columnas desconocidas.

## ⚙️ Requisitos
- Python 3
- pandas

Instalar pandas con: pip install pandas

## 🚀 Uso

Colocar limpieza_datos.py y uso_mensual.csv en la misma carpeta.

Luego ejecutar:
```
python limpieza_datos.py
```
El programa cargará automáticamente:
```
uso_mensual.csv
```
y realizará las validaciones y limpieza correspondientes.

## 🔍 ¿Qué valida el programa?
1. Validación de estructura

Antes de procesar los datos, el programa verifica que el archivo:

- Exista.
- No esté vacío.
- Sea un CSV válido.
- Contenga todas las columnas esperadas.
- No contenga columnas desconocidas.

Si existe algún problema estructural, el proceso se detiene y muestra un mensaje indicando que se debe revisar el archivo de uso mensual.

Por ejemplo:
```
ERROR: ARCHIVO DE USO MENSUAL NO VALIDO

El archivo de uso mensual no tiene una estructura válida.
 - Faltan columnas esperadas: productos_sincronizados
Se debe revisar el archivo de uso mensual subido antes de continuar.
```
Esto evita que otros procesos trabajen con información incompleta o con una estructura incorrecta.

## 🧹 Limpieza de datos

Cada columna tiene reglas específicas definidas en:
```
REGLAS_COLUMNAS
```
Estas reglas determinan:

Tipo de dato esperado.
Qué significa una celda vacía.
Rango permitido.
Formato esperado.
Valores permitidos.

De esta forma, si se necesita modificar una regla, se puede hacer directamente en REGLAS_COLUMNAS sin modificar el resto del código.

## Tipos de datos vacíos

El programa distingue diferentes situaciones.

- cero

Un valor vacío se transforma en:
```
0
```
Se utiliza cuando la ausencia del dato representa que no hubo actividad.

- error

Un valor vacío se considera inválido y provoca que la fila sea descartada.

- no_aplica

El valor vacío se mantiene como:
```
None
```
pero no se considera un error.

- marcar_vacio

El valor vacío se mantiene como:
```
None
```
pero la fila no se descarta.

Además, se genera un aviso para que pueda ser revisado posteriormente.

Actualmente esta lógica se utiliza para:
```
productos_sincronizados
```

## ✅ Validaciones cruzadas

Además de validar cada columna individualmente, el programa realiza comprobaciones entre columnas.

## Plan y MRR

El valor de mrr_usd debe corresponder al plan contratado:

| Plan | MRR (USD) |
|---|---:|
| Starter | 149 |
| Pro | 299 |
| Max | 549 |

Por ejemplo:
```
plan = pro
mrr_usd = 149
```
será considerado inconsistente.

Usuarios activos

El número de:
```
usuarios_activos_panel
```
no puede ser mayor que:
```
usuarios_cuenta
```
Si ocurre:
```
usuarios_activos_panel > usuarios_cuenta
```
la fila se considera inválida.

## 📊 Resultado del procesamiento

La función principal:
```
limpiar_dataset()
```
genera cuatro resultados principales:

- df_valido

Contiene las filas que cumplen todas las validaciones.

- df_descartadas

Contiene las filas que fueron descartadas por errores de validación.

- log

Contiene el detalle de las filas descartadas y el motivo.

Ejemplo:
```
fila_excel | cliente_id | mes     | motivos
1          | VSU-0001   | 2026-09 | mrr_usd (149) no coincide...
```

avisos
Contiene los datos faltantes que fueron detectados pero que no provocaron el descarte de la fila.

Esto permite diferenciar entre:

Datos que hacen que una fila sea inválida.
Datos faltantes que solamente requieren revisión.

## 📁 Archivos generados

La función:
```
exportar_resultados()
```
genera tres archivos CSV.

- uso_mensual_limpio.csv

Contiene únicamente los registros válidos y limpios.

- uso_mensual_log_descartes.csv

Contiene las filas descartadas y los motivos de cada descarte.

- uso_mensual_avisos.csv

Contiene los avisos relacionados con datos faltantes que no provocaron el descarte de la fila.

## 🛑 Manejo de errores

El programa utiliza una excepción específica:
```
ArchivoUsoMensualInvalido
```
Esta excepción se utiliza cuando el archivo uso_mensual.csv no puede ser procesado correctamente.

Entre las situaciones que detienen el proceso se encuentran:

- Archivo inexistente.
- Archivo completamente vacío.
- CSV con errores de lectura.
- Columnas faltantes.
- Columnas no reconocidas.
- Estructura incorrecta.

Cuando ocurre uno de estos casos, el programa termina con:
```
SystemExit(1)
```
Esto permite que otro script que dependa de este proceso pueda detectar que la validación falló y no continuar con el procesamiento posterior.

## 🔄 Flujo del programa

El funcionamiento general es:
```
uso_mensual.csv
       │
       ▼
Validar existencia y lectura
       │
       ▼
Validar estructura
       │
       ├── ❌ Error → detener proceso
       │
       ▼
Validar cada fila
       │
       ├── ❌ Fila inválida → descartar + registrar motivo
       │
       ├── ⚠️ Dato faltante → mantener fila + registrar aviso
       │
       └── ✅ Fila válida
       │
       ▼
Generar resultados
       │
       ├── uso_mensual_limpio.csv
       ├── uso_mensual_log_descartes.csv
       └── uso_mensual_avisos.csv
```

## 🧩 Integración con otros módulos

limpieza_datos.py funciona como una etapa previa al procesamiento de señales o alertas.

El módulo no determina señales de riesgo ni realiza scoring.

Su función es entregar datos confiables y dejar registrados los problemas encontrados.

Por lo tanto, un flujo típico puede ser:
```
uso_mensual.csv
       │
       ▼
limpieza_datos.py
       │
       ▼
Datos validados
       │
       ▼
alertar.py
       │
       ▼
Generación de alertas
```
Si la validación estructural falla, limpieza_datos.py genera una excepción y el flujo debe detenerse antes de ejecutar el módulo posterior.

## 📝 Modificar reglas

Las reglas de validación se encuentran en:
```
REGLAS_COLUMNAS
```
Por ejemplo:
```
"mrr_usd": {
    "tipo": "numero",
    "vacio_significa": "error",
    "rango": (149, 549),
}
```
Esto permite modificar fácilmente los criterios de validación sin alterar las funciones principales.

## 📌 Consideraciones
El archivo de entrada debe llamarse uso_mensual.csv, salvo que se especifique otra ruta al utilizar las funciones.
Los nombres de las columnas deben coincidir con los esperados.
Las filas inválidas no se incorporan al archivo limpio.
Los datos faltantes definidos como marcar_vacio no eliminan la fila.
Los motivos de descarte quedan registrados en un archivo independiente.
Los avisos de datos faltantes quedan registrados para su posterior revisión.
El módulo está diseñado para ejecutarse antes del módulo de generación de alertas.
