# AUTOMATIZACION POR CONEXION DE DATOS !!
""" En este script se usa la automatizacion nivel basico. Esta conexion actualiza los graficos basados en la base de datos de BigQuery, la cual esta constantemente registrando datos segun el uso. Esto ocurre sin que se tenga que abrir Anaconda prompt ni tocar el codigo. Se incluye un boton inteligente para forzar la actualizacion de la memoria.

Las limitacionees es que necesita estar constantemente actualizando el script en Github con el que esta conectado streamlit y BigQuery.

 """

import os
import requests
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

def enviar_telegram(mensaje):
    # 1. Intentamos sacar las llaves de Secrets (Streamlit Cloud)
    try:
        token = st.secrets["telegram"]["token"]
        raw_ids = str(st.secrets["telegram"]["chat_id"])
        destinatarios = [id.strip() for id in raw_ids.split(",")]
    except:
        # Si estás en local o fallan los secrets
        token = "8687826455:AAHtpcu9uiHBENsaTDl5nOC7U5EJ8XQ79nM"
        destinatarios = ["7114539076", "6507364524"] # Asegúrate que el segundo ID sea real

    # 2. Ciclo para enviar el mensaje a cada persona
    respuestas = []
    for persona_id in destinatarios:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": persona_id, "text": mensaje, "parse_mode": "Markdown"}
        try:
            r = requests.post(url, json=payload)
            respuestas.append(r)
        except Exception as e:
            print(f"Error enviando a {persona_id}: {e}")
            
    return respuestas # Devuelve la lista de respuestas

# ## Grafico de Lineas

# --- Logica de los Datos ---
sql_grafico2 = """
SELECT
    Fecha_Pago,
    ROUND(SUM(TOTAL)) AS Total_Ganancia,
    ROUND(SUM(Cantidad))
FROM `pan-database-491915.dataset.ventas_final`
WHERE TOTAL IS NOT NULL
GROUP BY Fecha_Pago
ORDER BY Fecha_Pago DESC
"""

try:
    df = cargar_datos(sql_grafico2)

    if df.empty:
        st.warning("No se encontraron datos validos para lanzar el grafico")
    else:
        st.subheader("Ganancia Total por Fecha")
        df["Fecha_Pago"] = pd.to_datetime(df["Fecha_Pago"])
        df = df.sort_values("Fecha_Pago")
        
        # 3. Creamos el gráfico usando seaborn.objects
        grafico = (
            so.Plot(df, x="Fecha_Pago", y="Total_Ganancia")
            .add(so.Line())
            .layout(size=(10,5))
        )

        # 4. Renderizamos y extraemos figura
        figura_final = grafico.plot()._figure

        # LIMPIEZA DEL EJE X
        for ax in figura_final.axes:
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=5))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax.get_xticklabels(), rotation=45)
        
        st.pyplot(figura_final)

except Exception as e:
    st.error(f"Error al generar el gráfico de líneas: {e}")

# ### Agrupados por Producto

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

try: 
    df = cargar_datos(sql_grafico3)

    if df.empty:
        st.warning("No se encontraron datos validos. Revisa la tabla de BigQuery")
    else:
        st.subheader("Ganancia Total por Fecha Agrupado por Producto")
        df["Fecha_Pago"] = pd.to_datetime(df["Fecha_Pago"])
        df = df.sort_values("Fecha_Pago")

        # Gráfico agrupado por color
        grafico2 = (
            so.Plot(df, x="Fecha_Pago", y="Total_Ganancia", color="Producto")
            .add(so.Line(linewidth=1), group="Producto")
            .layout(size=(10,6))
        )

        figura_final2 = grafico2.plot()._figure

        for ax in figura_final2.axes:
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=5))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax.get_xticklabels(), rotation=45)

        st.pyplot(figura_final2)

except Exception as e:
    st.error(f"Error al generar el grafico agrupado: {e}")

# --- CONSULTA 2: PARA EL RESUMEN DE TELEGRAM ---
# --- CONSULTA PARA TELEGRAM ---
query_resumen = """ 
    SELECT 
        Fecha_Pago,
        Producto,
        ROUND(SUM(TOTAL)) AS Total_Dia
    FROM `pan-database-491915.dataset.ventas_final`
    GROUP BY Producto, Fecha_Pago
    ORDER BY Fecha_Pago DESC
""" 

if st.button("🚀 Enviar Resumen a Telegram"):
    try:
        # 1. Obtener datos
        df_resumen = client.query(query_resumen).to_dataframe()
        
        if not df_resumen.empty:
            r = df_resumen.iloc[0]
            
            # 2. Formatear el mensaje
            fecha_str = r['Fecha_Pago']
            venta_total = r['Total_Dia']
            
            mensaje_formateado = (
                f"🥖 *REPORTE PAN PA TI* 🥖\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 *Día:* {fecha_str}\n"
                f"💰 *Venta Total:* ${venta_total:,.2f}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ _Cierre generado desde el Dashboard_"
            )
            
            # 3. Enviar
            respuesta = enviar_telegram(mensaje_formateado)
            
            if respuesta.status_code == 200:
                st.success("¡Mensaje enviado a Telegram! 📱")
            else:
                st.error(f"Telegram no recibió el mensaje: {respuesta.text}")
        else:
            st.warning("No se encontraron ventas para enviar.")
            
    except Exception as e:
        st.error(f"Error en el proceso de Telegram: {e}")
