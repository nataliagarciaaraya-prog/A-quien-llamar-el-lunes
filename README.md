# Versu AI
# Sistema de alertas de uso mensual

`alertar.py` es el módulo encargado de analizar el uso mensual de los clientes de Versu AI y generar alertas según diferentes situaciones detectadas en sus cuentas.

Este archivo trabaja junto con `limpieza_datos.py`. Primero se valida y limpia el archivo `uso_mensual.csv` y luego `alertar.py` utiliza los datos resultantes para evaluar las condiciones de alerta.

## ⚙️ Funcionamiento

El programa se ejecuta **una vez al mes** y determina automáticamente el mes que se está evaluando.

El flujo principal es:

```text
uso_mensual.csv
       ↓
limpieza_datos.py
       ↓
Datos limpios y validados
       ↓
alertar.py
       ↓
Evaluación de casos
       ↓
alertas_AAAA-MM.xlsx
```

Si el archivo original presenta errores de estructura, el proceso se detiene y **no se generan alertas**, indicando que el archivo debe ser revisado.

## 🚨 Casos evaluados

| Caso | Alerta | Condición |
|---|---|---|
| 1 | Cuenta huérfana | 0 usuarios activos durante el mes actual y el anterior |
| 2 | Agente inactivo | 2 o más días de agente inactivo |
| 4 | Excede plan | Las conversaciones superan el límite establecido para el plan |
| 5 | No despega | Cuenta con menos de 3 meses, pocas sesiones y menos del 50% del límite de conversaciones |

Los casos se reúnen en una única lista de alertas y se ordenan por plan:

**Max → Pro → Starter**

### Diagnósticos adicionales

- **Caso 3 – Estacionalidad:** analiza si existe una caída generalizada de conversaciones por rubro. Es un diagnóstico y no genera una alerta directa.
- **Caso 6 – Dato faltante:** identifica datos faltantes registrados durante la limpieza. Es un aviso adicional y no corresponde a los cuatro casos principales.

## 📊 Resultado

El programa genera un archivo Excel:

```text
alertas_AAAA-MM.xlsx
```

Este archivo incluye:

- ID del cliente
- Nombre del cliente
- Plan
- Teléfono
- Correo
- Situación detectada
- Mensaje sugerido para contactar al cliente

Los mensajes se generan automáticamente según el tipo de alerta detectada.

## Exclusiones
Lo que se dejó fuera:

Deduplicación histórica: Cada corrida evalúa el estado completo del mes actual independientemente de si la alerta ya fue notificada antes.

Automatización del envío: La salida requiere que un humano revise el Excel y envíe el mensaje.

Con una semana más de desarrollo:

- Implementar una base para registrar el historial de alertas y evitar renotificar la misma cuenta durante el mismo período.

- Reemplazar la generación de Excel por un envío automático o alertas directas en un canal de Slack/Teams.

- Realizar ajustes al Caso 3 por estacionalidad.