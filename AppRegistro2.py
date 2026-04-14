# AUTOMATIZACION DINAMICA DE GRAFICOS "Generador de Graficos"
""" En este script se trata automatizar la generacion de los graficos segun las combinaciones posibles entre las variables. 
Este script evita la actualizacion del codigo en Github. De modo que para cada grafico se puede generar ese mismo tipo 
de grafico segun la combinacion de variables seleccionables en la propia pagina web.

Limitaciones. El codigo esta basado exclusivamente en la oferta de datos codificada de BigQuery. 
Aunque, se puede establecer para un tipo de grafico distintas combinaciones, esta depende de la consulta inicial. 

Listo para lanzar
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sb
import numpy as np
import streamlit as st
import seaborn.objects as so
from google.oauth2 import service_account
from google.cloud import bigquery

## --- 1. Configuracion de los permisos y la conexion de los serivicios (Siempre al inicio) ---

st.set_page_config(page_title = "Dashboard dinamico Pan Pa Ti", layout="wide", page_icon="🍞")

### Seleccion de las credenciales de BigQuery "la llave maestra" de Google Cloud
ruta_json = r"C:\Users\alons\Desktop\Pan Pa ti\App Web\Spark\credenciales\pan-database-491915-a0418ffe970e.json"

### Definicion de los permisos de los servicios usados. La lista las acciones de la App 
scopes = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/cloud-platform"
]

### Creacion de la funcion de la conexion con los serivicios
@st.cache_resource # Guarda la conexion
def obtener_cliente():
    # Caso 1: Local (Si el archivo existe en la PC)
    if os.path.exists(ruta_json):
        # Si se encuentra el archivo en la computadora se usa
        # Tengo EL ARCHIVO -> Usa el comando para archivos
        credentials = service_account.Credentials.from_service_account_file(
            ruta_json, scopes = scopes
        )

    # Caso 2: Nube (Usa los secretos configurados en la web)
    else:
        # Si el archivo no existe se busca las credenciales en streamlit "Secrets"
        # No tengo EL ARCHIVO -> Usa el comando para Diccionarios/Texto (info)
        info = dict(st.secrets["gcp_service_account"])

        # Limpieza inteligente de la llave
        raw_key = info["private_key"]
        # Si la llave viene con el texto literal \n, lo convertimos a salto real
        if "\\n" in raw_key:
            info["private_key"] = raw_key.replace("\\n","\n")

        credentials = service_account.Credentials.from_service_account_info(
            info, scopes = scopes
        ) 

    return bigquery.Client(credentials = credentials, project ="pan-database-491915")

## ---- 2. Inicializacion del Cliente ----

### Funcion auxiliar para cargar datos
def cargar_datos(query):
    client = obtener_cliente()
    return client.query(query).to_dataframe()

client = obtener_cliente()

### --- 3. Interfaz del Usuario ---
st.title("🍞 Dashboard de Ventas Pan Pa ti")

# El botón solo sirve para "limpiar" y "reiniciar"
if st.button('🔄 Actualizar datos ahora'):
    st.cache_data.clear() # Esto borra los datos viejos guardados
    st.rerun()            # Esto obliga a la app a empezar de cero y leer BigQuery

### --- 4. LÓGICA DE LOS DATOS (Fuera del IF para que siempre funcione) ---

# Usamos comillas invertidas ` para la tabla y corregimos el GROUP BY
sql_grafico = """
    SELECT
        Producto,
        Fecha_Pago,
        ROUND(SUM(TOTAL)) AS Total_Ganancia
    FROM `pan-database-491915.dataset.ventas_final`
    WHERE TOTAL IS NOT NULL
    GROUP BY Producto, Fecha_Pago
    ORDER BY Fecha_Pago DESC
"""

try: 
    df3 = cargar_datos(sql_grafico)

    if df3.empty:
        st.warning("No se encontraron datos validos. Revisa la tabla de BigQuery")
    else:
        st.subheader("Ganancia Total por Fecha Agrupado por Producto")

        df3["Fecha_Pago"] = pd.to_datetime(df3["Fecha_Pago"])
        df3 = df3.sort_values("Fecha_Pago")

        ### ---- Inicio de la Automatizacion ----
        #### Obtencion de la lista de los productos
        lista_productos = df3["Producto"].unique().tolist()

        ### --- Creacion de un filtro (widget) para que el usuario elija ---
        #### Por defecto, seleccionamos los primeros 3 evitando su vacio
        productos_seleccionados = st.multiselect(
             " 🍞 Seleccion que productos quieres visualizar:",
             options = lista_productos,
             default=lista_productos[:3] if len(lista_productos) >= 3 else lista_productos
        )

        df_filtrado = df3[df3['Producto'].isin(productos_seleccionados)]

        if not df_filtrado.empty:
            grafico2 = (
                so.Plot(df_filtrado, x="Fecha_Pago", y="Total_Ganancia", color = "Producto")
                .add(so.Line(linewidth=2, marker='o'), group = "Producto")
                .layout(size=(10,6))
            )
    
            figura_final2 = grafico2.plot()._figure

            for ax in figura_final2.axes:
                ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=5))
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                plt.setp(ax.get_xticklabels(), rotation=45)

            st.pyplot(figura_final2)
         
        else:
            st.info("Selecciona al menos un producto en el menu de arriba para ver el grafico")

except Exception as e:
    st.error(f"Error al generar el grafico agrupado: {e}")          
    st.info("💡 Tip: Si el error es de permisos (403), comprueba que el email de la Service Account tenga acceso al archivo de origen")