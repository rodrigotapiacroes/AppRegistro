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
        ROUND(SUM(Cantidad)) AS `Total Vendido`
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
                "💳 Tipo de Venta": "Tipo_de_Venta",
                "📊 Impuesto IEPS (8%)": "ieps_8"
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