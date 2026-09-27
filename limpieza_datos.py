"""
limpieza_datos.py
-----------------------------------------------------------------------
Modulo de limpieza y validacion para uso_mensual.csv (version Python).
 
Traduce a codigo la tabla de decisiones que ya armaste:
  - que significa "vacio" en cada columna (cero real / no registrado / error /
    marcar_vacio -> no invalida la fila, pero queda registrado aparte)
  - que rango es valido
  - foto vs. tendencia (esta parte no se usa aca todavia; queda documentada
    para el modulo de senales que viene despues)
 
IMPORTANTE: las reglas viven en REGLAS_COLUMNAS, mas abajo. Si cambias un
criterio, lo editas ahi. No deberias necesitar tocar el resto del archivo
para eso.
 
Este modulo NO decide senales de riesgo ni scoring -- solo entrega datos
limpios + un log explicito de que se descarto/corrigio y por que.
 
Requiere: pandas (pip install pandas)
-----------------------------------------------------------------------
"""
 
import re
import pandas as pd
 
 
# =========================================================================
# 1. TABLA DE REGLAS POR COLUMNA
# =========================================================================
#
# tipo: "texto" | "numero" | "entero"
# vacio_significa:
#    "cero"         -> celda vacia se convierte en 0
#    "error"        -> celda vacia es un dato invalido, LA FILA SE DESCARTA
#    "no_aplica"    -> celda vacia es esperable, no es error, no se usa como 0
#    "marcar_vacio" -> celda vacia queda en None, NO invalida la fila, pero
#                      se registra en un log de "avisos" aparte (para poder
#                      alertar "falta este dato" sin descartar el resto de
#                      la fila para las demas senales)
# rango: (min, max). None si no aplica en ese extremo.
# exclusivo_min: True si el minimo NO incluye el valor exacto (> en vez de >=)
# valores_validos: lista cerrada de valores (solo para texto con set fijo)
# nota: lo que dejaste anotado en tu tabla, para que quede trazable
 
REGLAS_COLUMNAS = {
    "cliente_id": {
        "tipo": "texto",
        "vacio_significa": "error",
        "patron": r"^VSU-\d{4}$",
        "nota": "Formato esperado VSU-0001 a VSU-0140",
    },
    "cliente": {
        "tipo": "texto",
        "vacio_significa": "error",
        "nota": "Nombre del cliente, sin validacion de formato",
    },
    "mes": {
        "tipo": "texto",
        "vacio_significa": "error",
        "patron": r"^\d{4}-(0[5-9])$",  # formato real: "2026-05" .. "2026-09"
        "nota": "Formato real es 'AAAA-MM' (ej. 2026-05).",
    },
    "plan": {
        "tipo": "texto",
        "vacio_significa": "error",
        "valores_validos": ["starter", "pro", "max"],
        "nota": "Debe coincidir con mrr_usd (ver validacion cruzada mas abajo)",
    },
    "mrr_usd": {
        "tipo": "numero",
        "vacio_significa": "error",
        "rango": (149, 549),
        "nota": "149 / 299 / 549 segun plan. Se valida cruzado con 'plan' aparte.",
    },
    "conversaciones": {
        "tipo": "entero",
        "vacio_significa": "error",
        "rango": (0, None),
        "nota": "Total. Se comparan los demas campos de conversacion contra este.",
    },
    "resueltas_por_agente": {
        "tipo": "entero",
        "vacio_significa": "cero",
        "rango": (0, None),
    },
    "derivadas_a_humano": {
        "tipo": "entero",
        "vacio_significa": "cero",
        "rango": (0, None),
    },
    "derivadas_sin_respuesta": {
        "tipo": "entero",
        "vacio_significa": "cero",
        "rango": (0, None),
        "nota": "Si es muy alta respecto al total, senal de flujo alto sin cubrir",
    },
    "seg_respuesta_agente": {
        "tipo": "numero",
        "vacio_significa": "error",
        "rango": (0, None),
        "exclusivo_min": True,
        "nota": "TODO: confirmar si 0 segundos es fisicamente posible o debe ser error",
    },
    "carritos_recuperados": {
        "tipo": "entero",
        "vacio_significa": "cero",
        "rango": (0, None),
    },
    "ventas_atribuidas_usd": {
        "tipo": "numero",
        "vacio_significa": "cero",
        "rango": (0, None),
    },
    "sesiones_panel": {
        "tipo": "entero",
        "vacio_significa": "cero",
        "rango": (0, None),
    },
    "dias_activos_panel": {
        "tipo": "entero",
        "vacio_significa": "error",
        "rango": (0, None),
        "nota": "TODO SIN CERRAR: ver si 0 debe tratarse como alarma real, no como dato invalido.",
    },
    "usuarios_activos_panel": {
        "tipo": "entero",
        "vacio_significa": "cero",
        "rango": (0, None),
    },
    "usuarios_cuenta": {
        "tipo": "entero",
        "vacio_significa": "error",
        "rango": (0, None),
        "exclusivo_min": True,
    },
    "cambios_configuracion": {
        "tipo": "entero",
        "vacio_significa": "cero",
        "rango": (0, None),
    },
    "horas_respuesta_equipo": {
        "tipo": "numero",
        "vacio_significa": "cero",
        "rango": (0, None),
    },
    "tickets_soporte": {
        "tipo": "entero",
        "vacio_significa": "cero",
        "rango": (0, None),
    },
    "tickets_reabiertos": {
        "tipo": "entero",
        "vacio_significa": "cero",
        "rango": (0, None),
    },
    "errores_integracion": {
        "tipo": "entero",
        "vacio_significa": "cero",
        "rango": (0, None),
    },
    "dias_agente_inactivo": {
        "tipo": "entero",
        "vacio_significa": "cero",
        "rango": (0, 31),
    },
    "productos_sincronizados": {
        "tipo": "entero",
        "vacio_significa": "marcar_vacio",  # <-- CAMBIO PEDIDO: ya no descarta la fila
        "rango": (0, None),
        "nota": (
            "Vacio ya NO descarta la fila: queda en None y se registra en el "
            "log de avisos aparte, para generar una alerta de 'dato faltante' "
            "sin perder la fila para las demas senales."
        ),
    },
    "mensajes_no_entregados": {
        "tipo": "entero",
        "vacio_significa": "cero",
        "rango": (0, None),
    },
    "canales_activos": {
        "tipo": "texto",
        "vacio_significa": "error",
        "valores_validos": ["whatsapp", "instagram"],
        "es_lista": True,
        "nota": "Confirmar separador y codigos exactos con el archivo real",
    },
    "dias_pago_atrasado": {
        "tipo": "entero",
        "vacio_significa": "cero",
        "rango": (0, None),
    },
}
 
COLUMNAS_CURVA_ADOPCION = ["conversaciones", "carritos_recuperados"]
 
RANGO_MRR_POR_PLAN = {
    "starter": 149,
    "pro": 299,
    "max": 549,
}
 
 
# =========================================================================
# 2. VALIDACION DE ESTRUCTURA DEL ARCHIVO
# =========================================================================

class ArchivoUsoMensualInvalido(Exception):
    """Error bloqueante: el archivo uso_mensual.csv no puede procesarse."""


MENSAJE_ERROR_ARCHIVO = "Se debe revisar el archivo de uso mensual subido antes de continuar."


def validar_estructura(df: pd.DataFrame):
    errores = []
    columnas_esperadas = list(REGLAS_COLUMNAS.keys())
    columnas_presentes = list(df.columns) if df is not None else []

    if df is None or df.empty:
        errores.append("El archivo de uso mensual está vacío o no contiene filas de datos.")
    else:
        faltantes = [c for c in columnas_esperadas if c not in columnas_presentes]
        inesperadas = [c for c in columnas_presentes if c not in columnas_esperadas]

        if faltantes:
            errores.append(f"Faltan columnas esperadas: {', '.join(faltantes)}")
        if inesperadas:
            errores.append(
                f"Columnas no reconocidas en el archivo (revisar encabezado): {', '.join(inesperadas)}"
            )

    if errores:
        errores.append(MENSAJE_ERROR_ARCHIVO)

    return {"ok": len(errores) == 0, "errores": errores}


def cargar_uso_mensual(ruta: str = "uso_mensual.csv") -> pd.DataFrame:
    """Carga y valida el archivo. Si es inválido, detiene el flujo."""
    try:
        df = pd.read_csv(ruta)
    except FileNotFoundError:
        raise ArchivoUsoMensualInvalido(
            f"No se encontró el archivo '{ruta}'. {MENSAJE_ERROR_ARCHIVO}"
        )
    except pd.errors.EmptyDataError:
        raise ArchivoUsoMensualInvalido(
            f"El archivo '{ruta}' está completamente vacío. {MENSAJE_ERROR_ARCHIVO}"
        )
    except pd.errors.ParserError as e:
        raise ArchivoUsoMensualInvalido(
            f"No se pudo leer correctamente '{ruta}' (CSV inválido). "
            f"{MENSAJE_ERROR_ARCHIVO} Detalle: {e}"
        )

    estructura = validar_estructura(df)
    if not estructura["ok"]:
        detalle = "\n".join(
            f" - {e}" for e in estructura["errores"] if e != MENSAJE_ERROR_ARCHIVO
        )
        raise ArchivoUsoMensualInvalido(
            f"El archivo de uso mensual no tiene una estructura válida.\n"
            f"{detalle}\n{MENSAJE_ERROR_ARCHIVO}"
        )

    return df


# 3. LIMPIEZA DE UNA CELDA, SEGUN SU REGLA
# =========================================================================
 
def _celda_vacia(valor):
    if valor is None:
        return True
    if isinstance(valor, float) and pd.isna(valor):
        return True
    if isinstance(valor, str) and valor.strip() == "":
        return True
    return False
 
 
def limpiar_celda(nombre_columna, valor_crudo):
    regla = REGLAS_COLUMNAS[nombre_columna]
    problemas = []
    avisos = []
 
    # --- Vacio ---
    if _celda_vacia(valor_crudo):
        if regla["vacio_significa"] == "cero":
            return {"valor": 0, "valido": True, "problemas": problemas, "avisos": avisos}
        if regla["vacio_significa"] == "no_aplica":
            return {"valor": None, "valido": True, "problemas": problemas, "avisos": avisos, "no_aplica": True}
        if regla["vacio_significa"] == "marcar_vacio":
            avisos.append(
                f"{nombre_columna}: vacio (dato faltante -- revisar con Ops/plataforma; "
                f"no se descarta la fila)"
            )
            return {"valor": None, "valido": True, "problemas": problemas, "avisos": avisos}
        # "error"
        problemas.append(f"{nombre_columna}: vacio no permitido (se esperaba dato o 0 explicito)")
        return {"valor": None, "valido": False, "problemas": problemas, "avisos": avisos}
 
    # --- Texto ---
    if regla["tipo"] == "texto":
        valor = str(valor_crudo).strip()
 
        if regla.get("es_lista"):
            items = [s.strip().lower() for s in valor.split(",")]
            validos = regla.get("valores_validos")
            invalidos = [i for i in items if validos and i not in validos]
            if invalidos:
                problemas.append(f"{nombre_columna}: valores no reconocidos ({', '.join(invalidos)})")
                return {"valor": valor, "valido": False, "problemas": problemas, "avisos": avisos}
            return {"valor": items, "valido": True, "problemas": problemas, "avisos": avisos}
 
        patron = regla.get("patron")
        if patron and not re.match(patron, valor):
            problemas.append(f'{nombre_columna}: no cumple el formato esperado ("{valor}")')
            return {"valor": valor, "valido": False, "problemas": problemas, "avisos": avisos}
 
        validos = regla.get("valores_validos")
        if validos:
            valor_norm = valor.lower()
            if valor_norm not in validos:
                problemas.append(f'{nombre_columna}: valor "{valor}" fuera de la lista permitida')
                return {"valor": valor, "valido": False, "problemas": problemas, "avisos": avisos}
            valor = valor_norm
 
        return {"valor": valor, "valido": True, "problemas": problemas, "avisos": avisos}
 
    # --- Numerico / entero ---
    try:
        texto_num = str(valor_crudo).replace(",", ".")
        num = float(texto_num)
    except (ValueError, TypeError):
        problemas.append(f'{nombre_columna}: "{valor_crudo}" no es un numero valido')
        return {"valor": None, "valido": False, "problemas": problemas, "avisos": avisos}
 
    if regla["tipo"] == "entero" and not num.is_integer():
        problemas.append(f"{nombre_columna}: se esperaba un entero, llego {num}")
        return {"valor": num, "valido": False, "problemas": problemas, "avisos": avisos}
 
    if regla["tipo"] == "entero":
        num = int(num)
 
    rango = regla.get("rango")
    if rango:
        minimo, maximo = rango
        if minimo is not None:
            bajo_minimo = num <= minimo if regla.get("exclusivo_min") else num < minimo
            if bajo_minimo:
                etiqueta = f"{minimo}, exclusivo" if regla.get("exclusivo_min") else f"{minimo}"
                problemas.append(f"{nombre_columna}: {num} por debajo del minimo permitido ({etiqueta})")
                return {"valor": num, "valido": False, "problemas": problemas, "avisos": avisos}
        if maximo is not None and num > maximo:
            problemas.append(f"{nombre_columna}: {num} por encima del maximo permitido ({maximo})")
            return {"valor": num, "valido": False, "problemas": problemas, "avisos": avisos}
 
    return {"valor": num, "valido": True, "problemas": problemas, "avisos": avisos}
 
 
# =========================================================================
# 4. VALIDACIONES CRUZADAS (entre columnas de la misma fila)
# =========================================================================
 
def validaciones_cruzadas(fila_limpia: dict):
    problemas = []
 
    # plan vs. mrr_usd
    plan = fila_limpia.get("plan")
    mrr = fila_limpia.get("mrr_usd")
    if plan and mrr is not None:
        esperado = RANGO_MRR_POR_PLAN.get(plan)
        if esperado is not None and mrr != esperado:
            problemas.append(
                f'mrr_usd ({mrr}) no coincide con el esperado para plan "{plan}" ({esperado})'
            )
 
    # usuarios_activos_panel no deberia superar usuarios_cuenta
    activos = fila_limpia.get("usuarios_activos_panel")
    total_usuarios = fila_limpia.get("usuarios_cuenta")
    if activos is not None and total_usuarios is not None and activos > total_usuarios:
        problemas.append(
            f"usuarios_activos_panel ({activos}) supera a usuarios_cuenta ({total_usuarios})"
        )
 
    return problemas
 
 
# =========================================================================
# 5. LIMPIEZA DE UNA FILA COMPLETA
# =========================================================================
 
def limpiar_fila(fila_cruda: dict):
    fila_limpia = {}
    problemas_fila = []
    avisos_fila = []
 
    for columna in REGLAS_COLUMNAS:
        resultado = limpiar_celda(columna, fila_cruda.get(columna))
        fila_limpia[columna] = resultado["valor"]
        if resultado["problemas"]:
            problemas_fila.extend(resultado["problemas"])
        if resultado.get("avisos"):
            avisos_fila.extend(resultado["avisos"])
 
    problemas_fila.extend(validaciones_cruzadas(fila_limpia))
 
    return {
        "fila_limpia": fila_limpia,
        "valida": len(problemas_fila) == 0,
        "problemas": problemas_fila,
        "avisos": avisos_fila,
    }
 
 
# =========================================================================
# 6. FUNCION PRINCIPAL: limpia el dataset completo
# =========================================================================
 
def limpiar_dataset(df: pd.DataFrame):
    """
    Recibe un DataFrame crudo y devuelve:
      - ok: bool, False si fallo la validacion de estructura
      - errores_estructura: lista de mensajes (columnas faltantes/de mas)
      - df_valido: DataFrame con las filas limpias y validas (incluye filas
        con productos_sincronizados vacio -> queda como None en esa celda)
      - df_descartadas: DataFrame con las filas crudas descartadas (por
        columnas "error", no por "marcar_vacio")
      - log: DataFrame, una fila por descarte, con motivos
      - avisos: DataFrame, una fila por cada dato marcado "marcar_vacio"
        (por ahora solo productos_sincronizados), SIN que la fila se haya
        descartado. Sirve de insumo para una alerta de "dato faltante".
    """
    estructura = validar_estructura(df)
    if not estructura["ok"]:
        detalle = "\n".join(
            f" - {e}" for e in estructura["errores"] if e != MENSAJE_ERROR_ARCHIVO
        )
        raise ArchivoUsoMensualInvalido(
            f"El archivo de uso mensual no tiene una estructura válida.\n"
            f"{detalle}\n{MENSAJE_ERROR_ARCHIVO}"
        )
 
    filas_validas = []
    filas_descartadas_crudas = []
    log = []
    avisos_log = []
 
    for i, fila_cruda in enumerate(df.to_dict(orient="records")):
        resultado = limpiar_fila(fila_cruda)
 
        if resultado["avisos"]:
            avisos_log.append({
                "fila_excel": i + 1,
                "cliente_id": fila_cruda.get("cliente_id", "(sin cliente_id)"),
                "mes": fila_cruda.get("mes", "(sin mes)"),
                "avisos": "; ".join(resultado["avisos"]),
            })
 
        if resultado["valida"]:
            filas_validas.append(resultado["fila_limpia"])
        else:
            filas_descartadas_crudas.append(fila_cruda)
            log.append({
                "fila_excel": i + 1,
                "cliente_id": fila_cruda.get("cliente_id", "(sin cliente_id)"),
                "mes": fila_cruda.get("mes", "(sin mes)"),
                "motivos": "; ".join(resultado["problemas"]),
            })
 
    return {
        "ok": True,
        "errores_estructura": [],
        "df_valido": pd.DataFrame(filas_validas),
        "df_descartadas": pd.DataFrame(filas_descartadas_crudas),
        "log": pd.DataFrame(log, columns=["fila_excel", "cliente_id", "mes", "motivos"]),
        "avisos": pd.DataFrame(avisos_log, columns=["fila_excel", "cliente_id", "mes", "avisos"]),
    }
 
 
# =========================================================================
# 6b. EXPORTAR RESULTADOS A ARCHIVOS
# =========================================================================
 
def exportar_resultados(resultado: dict, carpeta: str = ".", prefijo: str = "uso_mensual"):
    """
    Guarda tres archivos CSV a partir del resultado de limpiar_dataset():
      - {prefijo}_limpio.csv        -> los datos ya limpios y validos
      - {prefijo}_log_descartes.csv -> filas descartadas, con motivo
      - {prefijo}_avisos.csv        -> datos faltantes que NO se descartaron
        (por ahora, productos_sincronizados vacio)
    """
    import os
 
    if not resultado["ok"]:
        print("No se exporta nada: hay errores de estructura sin resolver.")
        for e in resultado["errores_estructura"]:
            print(" -", e)
        return
 
    os.makedirs(carpeta, exist_ok=True)
    ruta_validos = os.path.join(carpeta, f"{prefijo}_limpio.csv")
    ruta_log = os.path.join(carpeta, f"{prefijo}_log_descartes.csv")
    ruta_avisos = os.path.join(carpeta, f"{prefijo}_avisos.csv")
 
    try:
        resultado["df_valido"].to_csv(ruta_validos, index=False)
        resultado["log"].to_csv(ruta_log, index=False)
        resultado["avisos"].to_csv(ruta_avisos, index=False)
    except PermissionError as e:
        print(
            "\nERROR AL GUARDAR: no se pudo escribir uno de los archivos CSV.\n"
            "Causa mas probable: el archivo esta abierto en Excel (u otro programa) "
            "ahora mismo -- cerralo y volve a correr este script.\n"
            "Si no esta abierto, revisa que el archivo no este marcado como "
            "'solo lectura', o que OneDrive no lo este sincronizando en este momento.\n"
            f"Detalle tecnico: {e}"
        )
        return
    print(f"Guardado: {ruta_validos} ({len(resultado['df_valido'])} filas validas)")
    print(f"Guardado: {ruta_log} ({len(resultado['log'])} filas descartadas, con motivo)")
    print(f"Guardado: {ruta_avisos} ({len(resultado['avisos'])} avisos de datos faltantes)")
 
 
# =========================================================================
# 7. EJEMPLO DE USO
# =========================================================================
 
if __name__ == "__main__":
    try:
        df_crudo = cargar_uso_mensual("uso_mensual.csv")
        resultado = limpiar_dataset(df_crudo)

        print(f"Filas validas: {len(resultado['df_valido'])}")
        print(f"Filas descartadas: {len(resultado['df_descartadas'])}")
        print(f"Avisos de datos faltantes (no descartados): {len(resultado['avisos'])}")
        print("\nLog de descartes:")
        print(resultado["log"].to_string(index=False))

        exportar_resultados(resultado)

    except ArchivoUsoMensualInvalido as e:
        print("\nERROR: ARCHIVO DE USO MENSUAL NO VALIDO")
        print(str(e))
        raise SystemExit(1)