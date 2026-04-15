# =================================================================
# SCRIPT: DashboardDinamico.py
# PROYECTO: Pan Pa Ti - Sistema de Business Intelligence
# OBJETIVO: Generar gráficos automatizados que cambian de dimensión
#           (Producto, Cliente, etc.) y métrica según el usuario.
# NIVEL: El nivel de este grafico es intemredio, genera grafico y no unicamente conexion con la base de datos
# =================================================================

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn.objects as so  # Librería moderna para gráficos dinámicos
import streamlit as st
from google.oauth2 import service_account
from google.cloud import bigquery

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
# Establece el título de la pestaña y el diseño ancho (pantalla completa)
st.set_page_config(page_title="BI Pan Pa Ti", layout="wide", page_icon="🍞")

# Ruta local de las credenciales (Solo funciona en tu PC)
ruta_json = r"C:\Users\alons\Desktop\Pan Pa ti\App Web\Spark\credenciales\pan-database-491915-a0418ffe970e.json"

# Permisos requeridos para que la app lea BigQuery y Google Drive
scopes = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/cloud-platform"
]

@st.cache_resource # Evita que la app se reconecte a Google en cada clic (mejora velocidad)
def obtener_cliente():
    """
    Gestiona la conexión: 
    Si detecta el archivo JSON (Local), lo usa. 
    Si no (Nube/Streamlit Cloud), usa los 'Secrets'.
    """
    if os.path.exists(ruta_json):
        credentials = service_account.Credentials.from_service_account_file(
            ruta_json, scopes=scopes
        )
    else:
        # Extrae las credenciales guardadas en la configuración de Streamlit Web
        info = dict(st.secrets["gcp_service_account"])
        if "\\n" in info["private_key"]:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=scopes
        )
    
    return bigquery.Client(credentials=credentials, project="pan-database-491915")

def cargar_datos(query):
    """Ejecuta la consulta SQL y la convierte en una tabla de Python (DataFrame)"""
    client = obtener_cliente()
    return client.query(query).to_dataframe()

# --- 2. CONSULTA SQL (El motor de los datos) ---
# Seleccionamos todas las columnas necesarias para que el Dashboard sea flexible
sql_grafico = """
    SELECT
        Fecha_Pago,
        Producto,
        Cliente,
        Tipo_Venta,
        aplica_ieps,
        ROUND(SUM(TOTAL)) AS Total_Ganancia,
        ROUND(SUM(Cantidad)) AS `Total Vendido`,
	COUNT(Producto) AS `Total Productos`
    FROM `pan-database-491915.dataset.ventas_final`
    WHERE TOTAL IS NOT NULL
    GROUP BY Fecha_Pago, Producto, Cliente, Tipo_Venta, aplica_ieps
    ORDER BY Fecha_Pago DESC
"""

# --- 3. INTERFAZ DE USUARIO ---
st.title("🍞 Dashboard Inteligente - Pan Pa Ti")

# Botón para forzar que la app traiga datos nuevos de la nube
if st.button('🔄 Actualizar Datos'):
    st.cache_data.clear()
    st.rerun()

try:
    # Intentamos cargar los datos desde BigQuery
    df_raw = cargar_datos(sql_grafico)

    if df_raw.empty:
        st.warning("La base de datos respondió, pero no hay registros para mostrar.")
    else:
        # Limpieza: Convertimos la columna de fecha a un formato que Python entienda bien
        df_raw["Fecha_Pago"] = pd.to_datetime(df_raw["Fecha_Pago"]).dt.date
        df_raw = df_raw.sort_values("Fecha_Pago")

        st.divider() # Línea visual divisoria

        # --- SELECTORES DINÁMICOS (Filtros en la parte superior) ---
        col_fecha, col_dim, col_metrica = st.columns([2, 2, 2])

        with col_fecha:
            # Filtro de Eje X (Zoom temporal)
            f_min, f_max = df_raw["Fecha_Pago"].min(), df_raw["Fecha_Pago"].max()
            rango_fechas = st.date_input("📅 Rango de tiempo:", value=(f_min, f_max))

        with col_dim:
            # Filtro de Dimensión (¿Qué queremos ver en los colores/líneas?)
            dict_dims = {
                "🍞 Productos": "Producto",
                "👤 Clientes": "Cliente",
                "💳 Tipo de Venta": "Tipo_Venta",
                "📊 Impuesto IEPS (8%)": "aplica_ieps"
            }
            dim_label = st.selectbox("🔍 Analizar por:", list(dict_dims.keys()))
            col_dim_actual = dict_dims[dim_label]

        with col_metrica:
            # Filtro de Eje Y (¿Qué valor queremos medir?)
            dict_mets = {
                "💰 Ganancia Total": "Total_Ganancia",
                "🛒 Cantidad de Ventas": "Total Vendido",
                "📦 Total de Productos":"Total Productos"
            }
            met_label = st.selectbox("📊 Métrica (Eje Y):", list(dict_mets.keys()))
            col_met_actual = dict_mets[met_label]

        # --- SELECTOR MULTIPLE DE ELEMENTOS ---
        # Permite elegir específicamente qué productos o clientes ver
        opciones_disponibles = sorted(df_raw[col_dim_actual].unique().tolist())
        seleccion = st.multiselect(
            f"Selecciona elementos de {dim_label}:",
            options=opciones_disponibles,
            default=opciones_disponibles[:3] if len(opciones_disponibles) >= 3 else opciones_disponibles
        )

        # --- APLICACIÓN DE FILTROS ---
        if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
            inicio, fin = rango_fechas
            mask = (
                (df_raw["Fecha_Pago"] >= inicio) & 
                (df_raw["Fecha_Pago"] <= fin) &
                (df_raw[col_dim_actual].isin(seleccion))
            )
            df_filtrado = df_raw.loc[mask]

            # --- 4. RENDERIZADO DEL GRÁFICO ---
            if not df_filtrado.empty:
                st.subheader(f"Evolución de {met_label} por {dim_label}")
                
                # Creamos el objeto gráfico: X es siempre fecha, Y y Color cambian según el usuario
                grafico = (
                    so.Plot(df_filtrado, x="Fecha_Pago", y=col_met_actual, color=col_dim_actual)
                    .add(so.Line(linewidth=2, marker='o'), group=col_dim_actual)
                    .label(x="Fecha", y=met_label, color=dim_label)
                    .layout(size=(11, 5))
                )

                # Ajustes estéticos finales
                fig = grafico.plot()._figure
                for ax in fig.axes:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
                    plt.setp(ax.get_xticklabels(), rotation=45)

                st.pyplot(fig)
            else:
                st.info("No hay datos que coincidan con los filtros seleccionados.")

except Exception as e:
    st.error(f"Hubo un error al procesar el código: {e}")

# try:
    # 1. CARGA E INICIALIZACIÓN DE DATOS
    df_raw = cargar_datos(sql_grafico)

    if df_raw.empty:
        st.warning("La base de datos respondió, pero no hay registros para mostrar.")
    else:
        # Preparación de fechas (Aseguramos formato fecha de Python)
        df_raw["Fecha_Pago"] = pd.to_datetime(df_raw["Fecha_Pago"]).dt.date
        df_raw = df_raw.sort_values("Fecha_Pago")

        st.divider()

        # --- 2. ÁREA DE FILTROS (SELECTORES) ---
        col_fecha, col_dim, col_metrica = st.columns([2, 2, 2])

        with col_fecha:
            f_min, f_max = df_raw["Fecha_Pago"].min(), df_raw["Fecha_Pago"].max()
            rango_fechas = st.date_input("📅 Rango de tiempo:", value=(f_min, f_max))

        with col_dim:
            dict_dims = {
                "🍞 Productos": "Producto",
                "👤 Clientes": "Cliente",
                "💳 Tipo de Venta": "Tipo_Venta",
                "📊 Aplica IEPS": "aplica_ieps",
                "📅 Fecha de Pago": "Fecha_Pago"
            }
            dim_label = st.selectbox("🔍 Analizar por (Dimensión):", list(dict_dims.keys()))
            col_dim_actual = dict_dims[dim_label]

        with col_metrica:
            dict_mets = {
                "💰 Ganancia Total": "Total_Ganancia",
                "🛒 Unidades Vendidas": "Total Vendido",
                "📦 Variedad de Productos": "Total Productos"
            }
            met_label = st.selectbox("📊 Métrica (Eje Y):", list(dict_mets.keys()))
            col_met_actual = dict_mets[met_label]

        # --- 3. SELECCIÓN DE ELEMENTOS ESPECÍFICOS ---
        opciones_disponibles = sorted(df_raw[col_dim_actual].unique().tolist())
        seleccion = st.multiselect(
            f"Selecciona elementos de {dim_label}:",
            options=opciones_disponibles,
            default=opciones_disponibles[:3] if len(opciones_disponibles) >= 3 else opciones_disponibles
        )

        # --- 4. FILTRADO DE DATOS ---
        if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
            inicio, fin = rango_fechas
            mask = (
                (df_raw["Fecha_Pago"] >= inicio) & 
                (df_raw["Fecha_Pago"] <= fin) &
                (df_raw[col_dim_actual].isin(seleccion))
            )
            df_filtrado = df_raw.loc[mask]

            if not df_filtrado.empty:
                
                # =========================================================
                # GRÁFICO 1: EVOLUCIÓN TEMPORAL (LÍNEAS)
                # =========================================================
                st.subheader(f"📈 Evolución Temporal: {met_label}")
                
                # Usamos seaborn.objects para un estilo moderno de líneas
                grafico_lineas = (
                    so.Plot(df_filtrado, x="Fecha_Pago", y=col_met_actual, color=col_dim_actual)
                    .add(so.Line(linewidth=2.5, marker='o'), group=col_dim_actual)
                    .label(x="Día", y=met_label, color=dim_label)
                    .layout(size=(12, 5))
                )
                
                # Ajuste de etiquetas de fecha en el gráfico de líneas
                fig_lineas = grafico_lineas.plot()._figure
                for ax in fig_lineas.axes:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
                    plt.setp(ax.get_xticklabels(), rotation=30)
                
                st.pyplot(fig_lineas)

                st.write("---") # Separador visual entre gráficos

                # =========================================================
                # GRÁFICO 2: COMPARATIVA GLOBAL (BARRAS)
                # =========================================================
                st.subheader(f"📊 Comparativa de Totales: {met_label}")

                # Agrupamos para obtener el total absoluto del periodo seleccionado
                df_barras = df_filtrado.groupby(col_dim_actual)[col_met_actual].sum().reset_index()
                
                # Orden inteligente: Cronológico si es fecha, Ranking si es texto
                if col_dim_actual == "Fecha_Pago":
                    df_barras = df_barras.sort_values(by="Fecha_Pago")
                else:
                    df_barras = df_barras.sort_values(by=col_met_actual, ascending=False)

                fig_barras, ax_bar = plt.subplots(figsize=(12, 6))
                colores = plt.cm.Paired(range(len(df_barras)))

                bars = ax_bar.bar(
                    df_barras[col_dim_actual].astype(str), 
                    df_barras[col_met_actual], 
                    color=colores, edgecolor='black', alpha=0.8
                )

                # Etiquetas de valor sobre las barras
                for bar in bars:
                    yval = bar.get_height()
                    ax_bar.text(
                        bar.get_x() + bar.get_width()/2, 
                        yval, f'{int(yval):,}', 
                        ha='center', va='bottom', fontweight='bold'
                    )

                ax_bar.set_ylabel(met_label)
                plt.xticks(rotation=45, ha='right')
                ax_bar.spines['top'].set_visible(False)
                ax_bar.spines['right'].set_visible(False)
                plt.tight_layout()

                st.pyplot(fig_barras)

                # TABLA DETALLADA (Expandible)
                with st.expander("📄 Ver detalles de la tabla de datos"):
                    st.dataframe(df_filtrado, use_container_width=True)

            else:
                st.info("No hay datos para mostrar con los filtros actuales.")

except Exception as e:
    st.error(f"Se detectó un error en la generación: {e}")
