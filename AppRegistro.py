import os
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from google.oauth2 import service_account
from google.cloud import bigquery

# --- 1. CONFIGURACIÓN DE LA PÁGINA (Siempre al inicio) ---
st.set_page_config(page_title="Dashboard Pan Pa Ti", layout="wide")

# --- 2. CREDENCIALES Y CLIENTE ---
ruta_json = r"C:\Users\alons\Desktop\Pan Pa ti\App Web\Spark\credenciales\pan-database-491915-a0418ffe970e.json"

scopes = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/cloud-platform"
]

@st.cache_resource
def obtener_cliente():
    # Caso 1: Local (Tu PC)
    if os.path.exists(ruta_json):
        credentials = service_account.Credentials.from_service_account_file(
            ruta_json, scopes=scopes
        )
    # Caso 2: Streamlit Cloud (Nube)
    else:
        # Extraemos el diccionario de los secretos de Streamlit
        info = dict(st.secrets["gcp_service_account"])
        
        # LIMPIEZA CRÍTICA DE LA LLAVE:
        # Reemplazamos los caracteres de texto "\n" por saltos de línea reales
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=scopes
        )
        
    return bigquery.Client(credentials=credentials, project="pan-database-491915")

# Inicializamos el cliente
client = obtener_cliente()

# --- 3. INTERFAZ DE USUARIO ---
st.title("🍞 Dashboard de Ventas Pan Pa Ti")

# Botón para forzar actualización
if st.button('🔄 Actualizar datos ahora'):
    st.cache_data.clear()
    st.rerun()

# --- 4. LÓGICA DE DATOS ---
sql_grafico = """
    SELECT
        Producto,
        SUM(Cantidad) as Total_Vendido
    FROM `pan-database-491915.dataset.ventas_final` 
    WHERE Folio != 'Folio'
        AND Cantidad IS NOT NULL
    GROUP BY Producto
    ORDER BY Total_Vendido DESC
"""

@st.cache_data
def cargar_datos(query):
    query_job = client.query(query)
    return query_job.to_dataframe()

# --- 5. EJECUCIÓN Y GRÁFICOS ---
try:
    df = cargar_datos(sql_grafico)

    if df.empty:
        st.warning("No se encontraron datos. Verifica la tabla en BigQuery.")
    else:
        # Creación del gráfico con Matplotlib
        fig, ax = plt.subplots(figsize=(12, 6))
        colores = plt.cm.Paired(range(len(df)))
        bars = ax.bar(df['Producto'], df['Total_Vendido'], 
                      color=colores, edgecolor='black', alpha=0.8)

        # Añadir etiquetas de valor sobre cada barra
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, 
                    yval + 0.1, 
                    str(int(yval)), 
                    ha='center', va='bottom', fontweight='bold')

        ax.set_title('Ventas Totales por Producto', fontsize=16, fontweight='bold')
        ax.set_ylabel('Unidades vendidas')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Renderizar en Streamlit
        st.pyplot(fig)
        
        # Tabla detallada oculta en un expander
        with st.expander("Ver tabla de datos detallada"):
            st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Error al generar el gráfico: {e}")
    st.info("💡 Tip: Si el error es de permisos (403), comprueba que el email de la Service Account tenga acceso al archivo origen.")