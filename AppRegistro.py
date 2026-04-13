import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st
from google.oauth2 import service_account
from google.cloud import bigquery
import seaborn as sns
import seaborn.objects as so

# --- 1. CONFIGURACIÓN DE LA PÁGINA (Siempre al inicio) ---
st.set_page_config(page_title="Dashboard Pan Pa Ti", layout="wide", page_icon="🍞")

# --- 2. CREDENCIALES Y CLIENTE ---
ruta_json = r"C:\Users\alons\Desktop\Pan Pa ti\App Web\Spark\credenciales\pan-database-491915-a0418ffe970e.json"

scopes = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/cloud-platform"
]

@st.cache_resource
def obtener_cliente():
    # Caso 1: Local
    if os.path.exists(ruta_json):
        credentials = service_account.Credentials.from_service_account_file(
            ruta_json, scopes=scopes
        )
    # Caso 2: Streamlit Cloud
    else:
        info = dict(st.secrets["gcp_service_account"])
        
        # Limpieza inteligente de la llave
        raw_key = info["private_key"]
        # Si la llave viene con el texto literal \n, lo convertimos a salto real
        if "\\n" in raw_key:
            info["private_key"] = raw_key.replace("\\n", "\n")
        
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

# ## Grafico de Barras

# --- 4. LÓGICA DE DATOS ---
sql_grafico = """
    SELECt
        Producto,
        SUM(Cantidad) as Total_Vendido
    FROM `pan-database-491915.dataset.ventas_final` 
    WHERE Folio != 'Folio'
	AND Producto IS NOT NULL
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

# ## Grafico de Lineas

# +
### Logica de los Datos

sql_grafico2 = """
SELECT
    Fecha_Pago,
    ROUND(SUM(TOTAL)) AS Total_Ganancia
FROM `pan-database-491915.dataset.ventas_final`
WHERE TOTAL IS NOT NULL
GROUP BY Fecha_Pago
ORDER BY Fecha_Pago DESC
"""

# +

try:
    df = cargar_datos(sql_grafico2)

    if df.empty:
        st.warning("No se encontraron datos validos para lanzar el grafico")

    else:

	st.subheader("Ganancia Total por Fecha")

	df["Fecha_Pago"] = pd.to_datetime(df["Fecha_Pago"])

	df = df.sort_values("Fecha_Pago") # Ordenacion cronologica
	
        # 3. Creamos el gráfico usando seaborn.objects
        # Usamos 'df' que es donde guardaste la consulta
        grafico = (
            so.Plot(df, x="Fecha_Pago", y="Total_Ganancia")
            .add(so.Line())
        )

	# 4. Renderizamos el gráfico a un objeto de Matplotlib
        figura_final = grafico.plot()._figure

	# LIMPIEZA DEL EJE X: solo mostrar 5 fechas de referencia

	for ax in figura_final.axes:
		ax.axes.set_major_locator(mdates.AutoDateLocator(maxticks=5))
		ax.axes.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
		plt.setp(ax.get.xticklabels(), rotation = 45)
        
        # 5. Mostramos el gráfico en Streamlit
        # La función .plot(figura_final) de seaborn.objects genera una figura de Matplotlib
        st.pyplot(figura_final)

except Exception as e:
    st.error(f"Error al generar el gráfico: {e}")
    st.info("💡 Tip: Si el error es de permisos (403), comprueba que el email de la Service Account tenga acceso al archivo origen.")
# -

# ### Agrupados por Producto

# +
# Logica de los Datos

sql_grafico3 = """
SELECT
  Producto,
  Fecha_Pago,
  ROUND(SUM(TOTAL)) AS Total_Ganancia
FROM `pan-database-491915.dataset.ventas_final`
WHERE TOTAL IS NOT NULL
GROUP BY 1, 2
ORDER BY Fecha_Pago DESC
"""

# +


try: 
    df = cargar_datos(sql_grafico3)

    if df.empty:
        st.warning("No se encontraron datos validos. Revisa la tabla de BigQuery")
    else:

	st.subheader("Ganancia Total por Fecha Agrupado por Producto")

	df["Fecha_Pago"] = pd.to_datetime(df["Fecha_Pago"])

	df = df.sort_values("Fecha_Pago") # Ordenacion cronologica

        grafico2 = (so.Plot(df, "Fecha_Pago", "Total_Ganancia", color="Producto")
        .add(so.Line(linewidth=1), group="Producto")
        )

	# 2. Renderizamos el gráfico a un objeto de Matplotlib
        figura_final2 = grafico2.plot()._figure

	# LIMPIEZA DEL EJE X: Solo mostrar 5 fechas de referencia

	for ax in figura_final2.axes:
		ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=5))
		ax.xaxis.set_major_formatter(mdates.DateFromatter('%Y-%m-%d'))
		plt.setp(ax.get_xticklabels(), rotation=45)

        st.pyplot(figura_final2)
    
except Exception as e:
    st.error(f"Error al generar el grafico: {e}")
    st.info(" Tip: Si el error es de permisos (403), comprueba que el email de la Service Account tenga acceso al archivo de origen.")
