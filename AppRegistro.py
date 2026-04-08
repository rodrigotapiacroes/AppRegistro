import os
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from google.oauth2 import service_account
from google.cloud import bigquery

# --- 1. CONFIGURACIÓN DE LA PÁGINA (Debe ser lo primero) ---
st.set_page_config(page_title="Dashboard Pan Pa Ti", layout="wide")

# --- 2. CREDENCIALES Y CLIENTE ---
# Definimos la ruta local
ruta_json = r"C:\Users\alons\Desktop\Pan Pa ti\App Web\Spark\credenciales\pan-database-491915-a0418ffe970e.json"

scopes = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/cloud-platform"
]

@st.cache_resource
def obtener_cliente():
    # Si el archivo existe localmente, lo usa. Si no (en la nube), usa secrets.
    if os.path.exists(ruta_json):
        credentials = service_account.Credentials.from_service_account_file(
            ruta_json, scopes=scopes
        )
    else:
        # Esto es para cuando lo subas a Streamlit Cloud
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes
        )
    return bigquery.Client(credentials=credentials, project="pan-database-491915")

client = obtener_cliente()

# --- 3. INTERFAZ DE USUARIO (Título y Botón) ---
st.title("🍞 Dashboard de Ventas Pan Pa Ti")

# Botón de actualización
if st.button('🔄 Actualizar datos ahora'):
    st.cache_data.clear()  # Limpia la memoria cache
    st.rerun()             # Recarga la app

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
        # --- CREACIÓN DEL GRÁFICO ---
        fig, ax = plt.subplots(figsize=(12, 6))
        
        colores = plt.cm.Paired(range(len(df)))
        bars = ax.bar(df['Producto'], df['Total_Vendido'], 
                      color=colores, edgecolor='black', alpha=0.8)

        # Etiquetas sobre las barras
        for bar in bars:
            yval = bar.get_height()
            ancho_barra = bar.get_width()
            ax.text(bar.get_x() + ancho_barra/2, 
                    yval + 0.1, 
                    str(int(yval)), 
                    ha='center', va='bottom', fontweight='bold')

        ax.set_title('Ventas Totales por Producto', fontsize=16, fontweight='bold')
        ax.set_ylabel('Unidades vendidas')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Mostrar el gráfico en la web
        st.pyplot(fig)
        
        # Opcional: Mostrar la tabla de datos debajo
        with st.expander("Ver datos detallados"):
            st.write(df)

except Exception as e:
    st.error(f"Error al generar el gráfico: {e}")
    st.info("💡 Si el error es 403, asegúrate de haber compartido el Google Sheet con el correo de la Service Account.")