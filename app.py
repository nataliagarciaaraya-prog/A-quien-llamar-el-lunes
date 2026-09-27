import streamlit as st
import pandas as pd
from alertar import generar_lista_alertas, diagnosticar_caso3_estacionalidad, evaluar_caso6_dato_faltante, generar_excel_alertas
from limpieza_datos import limpiar_dataset
from datetime import datetime

st.set_page_config(page_title="Sistema de Alertas Versu AI", layout="wide")

st.title("Sistema de Alertas de Clientes - Versu AI")

st.sidebar.header("Carga de Archivos")
file_uso = st.sidebar.file_uploader("Subir uso_mensual.csv", type=["csv"])
file_clientes = st.sidebar.file_uploader("Subir clientes.csv", type=["csv"])

mes_evaluado = st.sidebar.text_input("Mes a evaluar (AAAA-MM)", value=datetime.now().strftime("%Y-%m"))

if file_uso and file_clientes:
    df_crudo = pd.read_csv(file_uso)
    df_clientes = pd.read_csv(file_clientes, dtype={"telefono": str})

    resultado_limpieza = limpiar_dataset(df_crudo)

    if not resultado_limpieza["ok"]:
        st.error("Error en la estructura del archivo de uso mensual.")
        for err in resultado_limpieza["errores_estructura"]:
            st.write(f"- {err}")
    else:
        df_uso_limpio = resultado_limpieza["df_valido"]
        df_avisos = resultado_limpieza["avisos"]

        df_uso_limpio["mes"] = df_uso_limpio["mes"].astype(str)
        if not df_avisos.empty:
            df_avisos["mes"] = df_avisos["mes"].astype(str)

        st.subheader("Lista de Alertas del Mes")
        alertas = generar_lista_alertas(df_uso_limpio, df_clientes, mes_evaluado)

        if alertas.empty:
            st.success("No hay alertas generadas para este mes.")
        else:
            st.dataframe(alertas[["cliente_id", "plan", "mes", "caso", "motivo"]], use_container_width=True)

            ruta_excel = f"alertas_{mes_evaluado}.xlsx"
            generar_excel_alertas(alertas, df_clientes, mes_evaluado, ruta=ruta_excel)

            with open(ruta_excel, "rb") as f:
                st.download_button(
                    label="Descargar Alertas en Excel",
                    data=f,
                    file_name=ruta_excel,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        st.subheader("Diagnóstico de Estacionalidad por Rubro")
        diagnostico = diagnosticar_caso3_estacionalidad(df_uso_limpio, df_clientes, mes_evaluado)
        st.dataframe(diagnostico["tabla"], use_container_width=True)

        alertas_faltantes = evaluar_caso6_dato_faltante(df_avisos, mes_evaluado)
        if not alertas_faltantes.empty:
            st.subheader("Datos Faltantes a Corregir")
            st.dataframe(alertas_faltantes[["cliente_id", "mes", "motivo"]], use_container_width=True)
else:
    st.info("Por favor sube los dos archivos CSV desde el panel izquierdo para procesar las alertas.")