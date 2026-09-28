"""
alertar.py
-----------------------------------------------------------------------
Archivo unico de señales + ejecucion. Junto con limpieza_datos.py, son
los DOS archivos del proyecto:

  1) limpieza_datos.py  -> lee el Excel/CSV original, lo limpia, y
     EXPORTA: uso_mensual_limpio.csv, uso_mensual_log_descartes.csv,
     uso_mensual_avisos.csv

  2) alertar.py (este archivo) -> NO limpia nada. Lee esos CSV (mas
     clientes.csv) y calcula las alertas.

CADENCIA: MENSUAL (antes era semanal). Se corre una vez por mes, con
MES_ACTUAL apuntando al mes que se esta evaluando.

Los 4 casos alertables, actualizados segun tus nuevas reglas:

  Caso 1 - cuenta_huerfana:
      usuarios_activos_panel == 0 en el MES ACTUAL *y* en el MES ANTERIOR
      (dos meses seguidos, no uno solo)

  Caso 2 - agente_inactivo:
      dias_agente_inactivo >= 2 en el mes actual (sin cambios de logica)

  Caso 4 - excede_plan:
      conversaciones del mes actual supera el umbral de su plan:
      starter > 300, pro > 2000, max > 4000

  Caso 5 - no_despega:
      cuenta con menos de 3 meses de antiguedad, Y en el mes actual:
      sesiones_panel < 5  Y  conversaciones < 50% del umbral de su plan
      (starter: 150, pro: 1000, max: 2000)

Los 4 se muestran juntos en una sola lista final, ORDENADA POR PLAN
(max -> pro -> starter), indicando a que caso corresponde cada alerta.
Cada corrida muestra siempre el estado completo del mes (no hay
historial ni deduplicacion entre corridas -- se asume una corrida por mes).

Caso 3 (estacionalidad) sigue siendo diagnostico aparte, no una alerta.
Caso 6 (dato_faltante) sigue siendo un extra aparte, no uno de los 4.
-----------------------------------------------------------------------
"""

import pandas as pd

# =========================================================================
# CONFIG: todos los umbrales ajustables, en un solo lugar
# =========================================================================

CONFIG = {
    "caso2_dias_inactivo_min": 2,
    "caso5_meses_cuenta_nueva_max": 3,
    "caso5_sesiones_panel_max": 5,        # sesiones_panel < esto
    "caso5_pct_conversaciones_min": 0.5,  # conversaciones < este % del umbral del plan
    "caso3_umbral_caida_industria": 0.60,
}

# Umbral de conversaciones "normal" segun el plan (caso 4 y base del caso 5)
UMBRAL_CONVERSACIONES_PLAN = {
    "starter": 300,
    "pro": 2000,
    "max": 4000,
}

# Orden de plan para el listado final: max primero, starter al final
ORDEN_PLAN = {"max": 0, "pro": 1, "starter": 2}

CASO_LABELS = {
    "cuenta_huerfana": "Caso 1 - Cuenta huerfana",
    "agente_inactivo": "Caso 2 - Agente inactivo",
    "excede_plan": "Caso 4 - Conversaciones exceden el limite del plan",
    "no_despega": "Caso 5 - Cuenta nueva que no despega",
}

# Mensajes para el cliente, uno por tipo de alerta (a completar/ajustar
# el tono segun lo prefieras -- estos son un punto de partida razonable)
MENSAJES_POR_CASO = {
    "cuenta_huerfana": (
        "Hola {cliente},"
        "Te escribimos desde Versu AI. Queríamos saber cómo ha sido su experiencia con la plataforma, ya que hemos notado poco uso recientemente."
        "¿Han tenido algún inconveniente o hay algo en lo que podamos ayudarlos?"
        "Saludos,"
        "Natalia García / Versu AI"
    ),
    "agente_inactivo": (
        "Hola {cliente},"
        "Te escribimos desde Versu AI. Queríamos saber cómo ha estado funcionando el agente durante los últimos días y si han tenido algún inconveniente con su uso."
        "Quedamos atentos por si necesitan nuestro apoyo."
        "Saludos,"
        "Natalia García / Versu AI"
    ),
    "excede_plan": (
        "Hola {cliente},"
        "Te escribimos desde Versu AI. Hemos estado revisando su uso de la plataforma y nos gustaría saber cómo ha sido su experiencia hasta ahora."
        "Queremos asegurarnos de que cuenten con una solución que se adapte a sus necesidades actuales, por lo que estaremos encantados de conversar y revisar alternativas con ustedes."
        "Saludos,"
        "Natalia García / Versu AI"
    ),
    "no_despega": (
        "Hola {cliente},"
        "Te escribimos desde Versu AI. Queríamos saber cómo ha sido su experiencia durante estas primeras semanas con la plataforma."
        "Si tienen alguna duda o necesitan apoyo para aprovechar mejor sus funcionalidades, estaremos encantados de ayudarlos."
        "Saludos,"
        "Natalia García / Versu AI"
    ),
}

_MENSAJE_GENERICO = "Hola {cliente}, queremos conversar sobre el estado de tu cuenta este mes."

_COLUMNAS_ALERTA = ["cliente_id", "plan", "mes", "tipo_alerta", "motivo"]


def _sin_datos(columnas=_COLUMNAS_ALERTA) -> pd.DataFrame:
    return pd.DataFrame(columns=columnas)


def _mes_relativo(mes: str, delta: int) -> str:
    periodo = pd.Period(mes, freq="M") + delta
    return str(periodo)


# =========================================================================
# CASO 1 -- cuenta huerfana (mes actual Y mes anterior en 0)
# =========================================================================

def evaluar_caso1_cuenta_huerfana(df_uso: pd.DataFrame, mes_actual: str) -> pd.DataFrame:
    if df_uso.empty or "mes" not in df_uso.columns:
        return _sin_datos()

    mes_anterior = _mes_relativo(mes_actual, -1)

    actual = df_uso[df_uso["mes"] == mes_actual][
        ["cliente_id", "plan", "usuarios_activos_panel"]
    ].rename(columns={"usuarios_activos_panel": "usuarios_activos_actual"})

    anterior = df_uso[df_uso["mes"] == mes_anterior][
        ["cliente_id", "usuarios_activos_panel"]
    ].rename(columns={"usuarios_activos_panel": "usuarios_activos_anterior"})

    combinado = actual.merge(anterior, on="cliente_id", how="inner")
    alertas = combinado[
        (combinado["usuarios_activos_actual"] == 0)
        & (combinado["usuarios_activos_anterior"] == 0)
    ].copy()

    alertas["mes"] = mes_actual
    alertas["tipo_alerta"] = "cuenta_huerfana"
    alertas["motivo"] = (
        "0 usuarios activos en el panel durante " + mes_actual +
        " y " + mes_anterior + " (dos meses seguidos sin que nadie del cliente entre al panel)"
    )
    return alertas[_COLUMNAS_ALERTA]


# =========================================================================
# CASO 2 -- Agente caido sin detectar (sin cambios de logica, solo orden)
# =========================================================================

def evaluar_caso2_agente_caido(df_uso: pd.DataFrame, mes_actual: str) -> pd.DataFrame:
    columnas = _COLUMNAS_ALERTA + ["revisar_resolucion_previa"]
    if df_uso.empty or "mes" not in df_uso.columns:
        return _sin_datos(columnas)

    umbral = CONFIG["caso2_dias_inactivo_min"]
    filtro = df_uso[df_uso["mes"] == mes_actual].copy()
    alertas = filtro[filtro["dias_agente_inactivo"] >= umbral].copy()

    alertas["tipo_alerta"] = "agente_inactivo"
    alertas["motivo"] = (
        alertas["dias_agente_inactivo"].astype(str) +
        " dias de Agente inactivo en " + mes_actual
    )
    alertas["revisar_resolucion_previa"] = alertas["errores_integracion"] > 0

    return alertas[columnas]


# =========================================================================
# CASO 3 -- estacionalidad por rubro (DIAGNOSTICO, no alerta directa)
# =========================================================================

def diagnosticar_caso3_estacionalidad(
    df_uso: pd.DataFrame,
    df_clientes: pd.DataFrame,
    mes_actual: str,
    columna_metrica: str = "conversaciones",
) -> dict:
    if df_uso.empty or "mes" not in df_uso.columns:
        return {"tabla": pd.DataFrame(), "rubros_en_baja_generalizada": []}

    mes_anterior = _mes_relativo(mes_actual, -1)
    datos = df_uso[df_uso["mes"].isin([mes_actual, mes_anterior])].merge(
        df_clientes[["cliente_id", "rubro"]], on="cliente_id", how="left"
    )

    promedio = datos.groupby(["rubro", "mes"])[columna_metrica].mean().unstack()

    if mes_actual not in promedio.columns or mes_anterior not in promedio.columns:
        return {"tabla": promedio.reset_index(), "rubros_en_baja_generalizada": []}

    promedio["variacion_pct"] = (
        (promedio[mes_actual] - promedio[mes_anterior]) / promedio[mes_anterior]
    )

    umbral = CONFIG["caso3_umbral_caida_industria"]
    rubros_en_baja = promedio[promedio["variacion_pct"] <= -umbral].index.tolist()

    return {"tabla": promedio.reset_index(), "rubros_en_baja_generalizada": rubros_en_baja}


# =========================================================================
# CASO 4 -- conversaciones exceden el limite normal del plan
# =========================================================================

def evaluar_caso4_excede_plan(df_uso: pd.DataFrame, mes_actual: str) -> pd.DataFrame:
    if df_uso.empty or "mes" not in df_uso.columns:
        return _sin_datos()

    filtro = df_uso[df_uso["mes"] == mes_actual].copy()
    filtro["umbral_conversaciones"] = filtro["plan"].map(UMBRAL_CONVERSACIONES_PLAN)

    alertas = filtro[filtro["conversaciones"] > filtro["umbral_conversaciones"]].copy()
    alertas["tipo_alerta"] = "excede_plan"
    alertas["motivo"] = (
        "conversaciones (" + alertas["conversaciones"].astype(str) +
        ") supera el limite normal de su plan '" + alertas["plan"] + "' (" +
        alertas["umbral_conversaciones"].astype(str) + ") en " + mes_actual
    )
    return alertas[_COLUMNAS_ALERTA]


# =========================================================================
# CASO 5 -- cuenta nueva que no despega
# (antiguedad < 3 meses) Y (sesiones_panel < 5) Y (conversaciones < 50%
# del umbral normal de su plan)
# =========================================================================

def evaluar_caso5_no_despega(
    df_uso: pd.DataFrame, df_clientes: pd.DataFrame, mes_actual: str
) -> pd.DataFrame:
    if df_uso.empty or "mes" not in df_uso.columns:
        return _sin_datos()

    datos_clientes = df_clientes[["cliente_id", "fecha_checkout"]].copy()
    datos_clientes["fecha_checkout"] = pd.to_datetime(datos_clientes["fecha_checkout"])

    fin_mes_actual = pd.Period(mes_actual, freq="M").to_timestamp(how="end")
    datos_clientes["antiguedad_meses"] = (
        (fin_mes_actual.year - datos_clientes["fecha_checkout"].dt.year) * 12
        + (fin_mes_actual.month - datos_clientes["fecha_checkout"].dt.month)
    )

    umbral_antiguedad = CONFIG["caso5_meses_cuenta_nueva_max"]
    cuentas_nuevas = datos_clientes[datos_clientes["antiguedad_meses"] < umbral_antiguedad]["cliente_id"]

    filtro = df_uso[
        (df_uso["mes"] == mes_actual) & (df_uso["cliente_id"].isin(cuentas_nuevas))
    ].copy()
    filtro["umbral_conversaciones"] = filtro["plan"].map(UMBRAL_CONVERSACIONES_PLAN)
    filtro["umbral_conversaciones_50pct"] = (
        filtro["umbral_conversaciones"] * CONFIG["caso5_pct_conversaciones_min"]
    )

    umbral_sesiones = CONFIG["caso5_sesiones_panel_max"]
    condicion = (
        (filtro["sesiones_panel"] < umbral_sesiones)
        & (filtro["conversaciones"] < filtro["umbral_conversaciones_50pct"])
    )
    alertas = filtro[condicion].copy()

    alertas["tipo_alerta"] = "no_despega"
    alertas["motivo"] = (
        "sesiones_panel=" + alertas["sesiones_panel"].astype(str) +
        " y conversaciones=" + alertas["conversaciones"].astype(str) +
        " (menos del 50% de " + alertas["umbral_conversaciones"].astype(str) +
        " para su plan) en " + mes_actual +
        f" (cuenta con menos de {umbral_antiguedad} meses)"
    )
    return alertas[_COLUMNAS_ALERTA]


# =========================================================================
# CASO 6 (bonus, no es uno de los 4/5 casos) -- dato faltante
# =========================================================================

def evaluar_caso6_dato_faltante(df_avisos: pd.DataFrame, mes_actual: str) -> pd.DataFrame:
    columnas = ["cliente_id", "mes", "tipo_alerta", "motivo"]
    if df_avisos is None or df_avisos.empty or "mes" not in df_avisos.columns:
        return pd.DataFrame(columns=columnas)

    filtro = df_avisos[df_avisos["mes"] == mes_actual].copy()
    if filtro.empty:
        return pd.DataFrame(columns=columnas)

    filtro["tipo_alerta"] = "dato_faltante"
    filtro["motivo"] = filtro["avisos"]
    return filtro[columnas]


# =========================================================================
# FUNCION PRINCIPAL: junta los 4 casos alertables y los ordena por plan
# (max -> pro -> starter)
# =========================================================================

def generar_lista_alertas(
    df_uso_limpio: pd.DataFrame,
    df_clientes: pd.DataFrame,
    mes_actual: str,
) -> pd.DataFrame:
    if df_uso_limpio.empty or "mes" not in df_uso_limpio.columns:
        print(
            "ADVERTENCIA: no hay filas limpias para evaluar. Revisa "
            "uso_mensual_log_descartes.csv antes de seguir."
        )
        return _sin_datos()

    piezas = [
        evaluar_caso1_cuenta_huerfana(df_uso_limpio, mes_actual),
        evaluar_caso2_agente_caido(df_uso_limpio, mes_actual)[_COLUMNAS_ALERTA],
        evaluar_caso4_excede_plan(df_uso_limpio, mes_actual),
        evaluar_caso5_no_despega(df_uso_limpio, df_clientes, mes_actual),
    ]
    todas = pd.concat(piezas, ignore_index=True)

    if todas.empty:
        return todas

    todas["_orden_plan"] = todas["plan"].map(ORDEN_PLAN).fillna(99)
    todas = todas.sort_values(["_orden_plan", "cliente_id"]).drop(columns="_orden_plan")
    todas["caso"] = todas["tipo_alerta"].map(CASO_LABELS)

    return todas[["cliente_id", "plan", "mes", "tipo_alerta", "caso", "motivo"]]


# =========================================================================
# EXPORTAR LA LISTA A EXCEL, con los datos de contacto del cliente y un
# mensaje sugerido por caso
# =========================================================================

def generar_excel_alertas(
    alertas: pd.DataFrame, df_clientes: pd.DataFrame, mes_actual: str, ruta: str = None
) -> str:
    """
    Junta la lista de alertas con los datos de contacto de clientes.csv y
    guarda un Excel con las columnas: id_cliente, cliente, telefono, correo,
    situacion del caso, mensaje.

    Si una misma cuenta tiene mas de una alerta el mismo mes, aparece una
    fila por cada alerta (para no perder ningun motivo).
    """
    if ruta is None:
        ruta = f"alertas_{mes_actual}.xlsx"

    columnas_necesarias = ["cliente_id", "cliente", "telefono", "contacto_email"]
    faltantes = [c for c in columnas_necesarias if c not in df_clientes.columns]
    if faltantes:
        raise KeyError(
            f"clientes.csv no tiene estas columnas esperadas: {faltantes}. "
            f"Revisa los nombres reales de las columnas de contacto en tu archivo "
            f"y ajustalos en generar_excel_alertas()."
        )

    if alertas.empty:
        final = pd.DataFrame(
            columns=["id_cliente", "cliente", "telefono", "correo", "situación del caso", "mensaje"]
        )
    else:
        base = alertas.merge(
            df_clientes[columnas_necesarias], on="cliente_id", how="left"
        )
        final = pd.DataFrame({
            "id_cliente": base["cliente_id"],
            "cliente": base["cliente"],
            "plan": base["plan"],
            "telefono": base["telefono"],
            "correo": base["contacto_email"],
            "situación del caso": base["caso"] + " -- " + base["motivo"],
            "mensaje": [
                MENSAJES_POR_CASO.get(tipo, _MENSAJE_GENERICO).format(cliente=nombre)
                for tipo, nombre in zip(base["tipo_alerta"], base["cliente"])
            ],
        })

    final.to_excel(ruta, index=False, engine="openpyxl")

    from openpyxl import load_workbook
    from openpyxl.styles import Font

    wb = load_workbook(ruta)
    ws = wb.active
    fuente = Font(name="Arial", size=10)
    fuente_encabezado = Font(name="Arial", size=10, bold=True)
    for fila in ws.iter_rows():
        for celda in fila:
            celda.font = fuente_encabezado if celda.row == 1 else fuente

    anchos = {"A": 12, "B": 24, "C": 16, "D": 26, "E": 55, "F": 75}
    for col, ancho in anchos.items():
        ws.column_dimensions[col].width = ancho

    # Forzar formato de texto en la columna telefono (columna C), para que
    # Excel no le borre el "+" inicial ni ceros a la izquierda al abrirlo
    for fila in range(2, ws.max_row + 1):
        ws[f"C{fila}"].number_format = "@"

    wb.save(ruta)
    print(f"Guardado: {ruta} ({len(final)} filas)")
    return ruta


# =========================================================================
# EJECUCION: esto es lo que corre cada MES
# =========================================================================

if __name__ == "__main__":
    from limpieza_datos import limpiar_dataset, exportar_resultados
    from datetime import datetime
    ahora = datetime.now()

    # Formatea la fecha como 'Año-Mes' (ej. 2026-09)
    MES_ACTUAL = ahora.strftime("%Y-%m")

    print(MES_ACTUAL)# <-- cambiar cada mes segun el mes evaluado

    # --- Paso 0 (NUEVO): correr la limpieza ACA MISMO, antes de leer nada ---
    # Ya no hace falta acordarse de correr limpieza_datos.py aparte: si el
    # archivo original cambio, esto siempre trabaja con la version mas
    # reciente.
    try:
        df_crudo = pd.read_csv("uso_mensual.csv")
    except FileNotFoundError:
        raise SystemExit(
            "No encontre 'uso_mensual.csv' en esta carpeta. Poné el archivo "
            "original ahi (o ajusta la ruta en esta linea) antes de correr alertar.py."
        )

    resultado_limpieza = limpiar_dataset(df_crudo)

    if not resultado_limpieza["ok"]:
        print("ERRORES DE ESTRUCTURA -- no se pudo limpiar el archivo:")
        for e in resultado_limpieza["errores_estructura"]:
            print(" -", e)
        raise SystemExit(
            "Corregi el archivo original y volve a correr alertar.py. "
            "No se genero ninguna alerta."
        )

    exportar_resultados(resultado_limpieza)  # deja los 3 CSV en disco, como antes

    print(
        f"\nLimpieza: {len(resultado_limpieza['df_valido'])} filas validas, "
        f"{len(resultado_limpieza['df_descartadas'])} descartadas, "
        f"{len(resultado_limpieza['avisos'])} avisos de datos faltantes.\n"
    )

    # --- Paso 1: leer lo que se acaba de generar (igual que antes) ---
    df_uso_limpio = pd.read_csv("uso_mensual_limpio.csv")
    try:
        df_avisos = pd.read_csv("uso_mensual_avisos.csv")
    except pd.errors.EmptyDataError:
        df_avisos = pd.DataFrame(columns=["fila_excel", "cliente_id", "mes", "avisos"])
    df_clientes = pd.read_csv("clientes.csv", dtype={"telefono": str})

    df_uso_limpio["mes"] = df_uso_limpio["mes"].astype(str)
    if not df_avisos.empty:
        df_avisos["mes"] = df_avisos["mes"].astype(str)

    print(f"Filas de uso limpias cargadas: {len(df_uso_limpio)}")
    print(f"Clientes cargados: {len(df_clientes)}")
    print(f"Mes evaluado: {MES_ACTUAL}\n")

    alertas = generar_lista_alertas(df_uso_limpio, df_clientes, MES_ACTUAL)

    print("=" * 70)
    print("LISTA DE ALERTAS DEL MES (ordenada por plan: max -> pro -> starter)")
    print("=" * 70)
    if alertas.empty:
        print("(sin alertas nuevas este mes)")
    else:
        print(alertas[["cliente_id", "plan", "mes", "caso", "motivo"]].to_string(index=False))

    print("\n" + "=" * 70)
    print("CASO 3 - Diagnostico de estacionalidad por rubro (no es alerta)")
    print("=" * 70)
    diagnostico3 = diagnosticar_caso3_estacionalidad(df_uso_limpio, df_clientes, MES_ACTUAL)
    print(diagnostico3["tabla"].to_string(index=False))
    if diagnostico3["rubros_en_baja_generalizada"]:
        print(f"\nRubros con caida generalizada este mes: {diagnostico3['rubros_en_baja_generalizada']}")
    else:
        print("\nNingun rubro muestra caida generalizada este mes.")

    alertas_dato_faltante = evaluar_caso6_dato_faltante(df_avisos, MES_ACTUAL)
    if not alertas_dato_faltante.empty:
        print("\n" + "=" * 70)
        print("EXTRA - Datos faltantes a corregir (no es uno de los casos anteriores)")
        print("=" * 70)
        print(alertas_dato_faltante[["cliente_id", "mes", "motivo"]].to_string(index=False))

    # --- Nuevo: guardar la lista en Excel, con contacto del cliente y mensaje sugerido ---
    print()
    generar_excel_alertas(alertas, df_clientes, MES_ACTUAL)