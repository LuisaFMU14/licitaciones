import streamlit as st
import pandas as pd
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import io
import re

# Configuración de la clave y endpoint de Azure
endpoint = "https://licitaciones2.cognitiveservices.azure.com/"
api_key = "1I7xb68pTty5IPlFp0mXlfcYEhFWl5Veto7naJw4UeBDh6jcntytJQQJ99AKACYeBjFXJ3w3AAALACOGnrvO"

# Inicializar cliente de Azure Document Intelligence
client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))

# Valores predeterminados para comparar
valores_predeterminados = {
    "Índice de liquidez": "18,59",
    "Índice de endeudamiento": "0,05",
    "Razón de cobertura de intereses": "254,68",
    "Rentabilidad del patrimonio": "0,09",
    "Rentabilidad del activo": "0,09"
}

# Otros campos clave a buscar
campos_clave = [
    "Tipo de licenciamiento del proceso", 
    "Cantidades de licencias", 
    "Tiempo de uso",
    "Características de las licencias solicitadas",
    "Póliza de seriedad de la oferta",
    "Certificaciones solicitadas",
    "Experiencia solicitada"
]

# Función para analizar el documento
def analizar_documento(file):
    poller = client.begin_analyze_document("prebuilt-document", file)
    resultado = poller.result()
    texto_completo = ""
    
    for page in resultado.pages:
        for line in page.lines:
            texto_completo += line.content + "\n"
    
    return texto_completo

# Función para normalizar el texto (quitar espacios extra, saltos de línea innecesarios, etc.)
def normalizar_texto(texto):
    texto = texto.lower()  # Convertir a minúsculas para no diferenciar entre mayúsculas/minúsculas
    texto = re.sub(r'\s+', ' ', texto)  # Reemplazar múltiples espacios por uno solo
    texto = re.sub(r'\n+', ' ', texto)  # Eliminar saltos de línea excesivos
    texto = texto.strip()  # Eliminar espacios al principio y al final
    return texto

# Función para comparar los valores predeterminados con los encontrados
def verificar_valores(texto, valores_predeterminados):
    resultados_comparados = []

    texto_normalizado = normalizar_texto(texto)
    
    for campo, valor_predeterminado in valores_predeterminados.items():
        # Buscar el valor en el texto (ignorando mayúsculas/minúsculas)
        encontrado = re.search(rf"\b{re.escape(valor_predeterminado)}\b", texto_normalizado)
        
        if encontrado:
            cumple = "Cumple"
            valor_encontrado = valor_predeterminado
        else:
            cumple = "No Cumple"
            valor_encontrado = "No encontrado"
        
        resultados_comparados.append([campo, valor_predeterminado, valor_encontrado, cumple])

    return resultados_comparados

# Función para extraer campos clave del texto
def extraer_campos_clave(texto, campos_clave):
    resultados_campos = []
    
    texto_normalizado = normalizar_texto(texto)
    
    for campo in campos_clave:
        # Buscar el campo clave y el texto siguiente hasta un salto de línea
        encontrado = re.search(rf"({re.escape(campo)}[\s\S]*?)(?=\n|$)", texto_normalizado)
        
        if encontrado:
            respuesta = encontrado.group(1).strip()
        else:
            respuesta = "No encontrado"
        
        resultados_campos.append([campo, respuesta])

    return resultados_campos

# Crear la interfaz de usuario de Streamlit
st.title("Análisis de Pliego de Licitación")

st.markdown("""
    Esta aplicación permite subir un pliego de licitación (PDF o imagen)
    y extraer los datos utilizando el servicio de Document Intelligence de Azure.
""")

# Subir archivo
archivo = st.file_uploader("Sube el pliego de licitación", type=["pdf", "jpg", "jpeg", "png"])

if archivo:
    st.write("Analizando el documento...")

    # Llamar a la función para analizar el documento
    texto_completo = analizar_documento(archivo)

    # Verificar los valores predeterminados
    resultados_comparados = verificar_valores(texto_completo, valores_predeterminados)
    
    # Crear un DataFrame para los valores comparados
    df_valores = pd.DataFrame(resultados_comparados, columns=["Texto", "Valor Predeterminado", "Valor Encontrado", "Cumple"])

    # Mostrar la tabla de valores comparados
    st.subheader("Resultados de la Comparación")
    st.dataframe(df_valores)

    # Extraer los campos clave
    resultados_campos = extraer_campos_clave(texto_completo, campos_clave)
    
    # Crear un DataFrame para los campos clave
    df_campos = pd.DataFrame(resultados_campos, columns=["Campo", "Respuesta"])

    # Mostrar la tabla de campos clave
    st.subheader("Resultados de los Campos Clave")
    st.dataframe(df_campos)

    # Crear un archivo Excel con los resultados
    with pd.ExcelWriter("resultados_licitacion.xlsx") as writer:
        df_valores.to_excel(writer, sheet_name="Valores Comparados", index=False)
        df_campos.to_excel(writer, sheet_name="Campos Clave", index=False)

    # Enlace para descargar el archivo
    st.download_button(
        label="Descargar resultados en Excel",
        data=open("resultados_licitacion.xlsx", "rb").read(),
        file_name="resultados_licitacion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
