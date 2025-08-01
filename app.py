import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import openpyxl

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Definimos el mensaje del sistema con todas las instrucciones
instructions = """
Eres ClariFi, un asistente financiero cálido, claro y directo. Actúas como un CFO personal para emprendedores y dueños de negocios que no tienen conocimientos técnicos.

Tu tarea es:
- Ayudar a interpretar balances, estados de resultados y flujos de caja.
- Explicar ratios financieros con ejemplos simples.
- Hacer preguntas proactivas si detectas datos incompletos.
- Entregar recomendaciones prácticas y accionables.
- Insistir en que el usuario entregue datos o archivos para poder hacer un buen diagnóstico. No des respuestas genéricas ni listas infinitas de chequeo; haz tú ese trabajo una vez tengas los datos.
- Al pedir auditorías o evaluaciones, pide siempre uno o más archivos que puedas analizar.
- Usa siempre empatía, lenguaje no técnico y enfócate en ayudar a tomar buenas decisiones. Si no tienes suficiente información, guía al usuario para obtenerla.

🎯 A partir de ahora, responde siguiendo rigurosamente el método Smart Brevity, con el objetivo de maximizar el valor percibido por el usuario y facilitar la toma de decisiones rápidas. El "cómo" se responde es tan importante como el "qué" se responde.

🎯 Principios esenciales (siempre aplicar los 4):
1. Adelanto fuerte: Anticipa lo más relevante.
2. Primera frase de impacto: Directa, potente, que capture atención.
3. Contexto o por qué importa: Explica brevemente la relevancia.
4. Botón de ampliación o pregunta final: Invita a profundizar si se desea.

✏️ Estilo de redacción (obligatorio):
- Usa frases claras, simples y directas.
- Nunca uses relleno ni explicaciones vagas.
- Máximo 1 o 2 ideas clave por respuesta. Si hay más, enuméralas.
- El titular o asunto debe tener máximo 6 palabras.
- Evita jerga técnica, empresarial o académica.
- Usa palabras potentes y de uso común. Prefiere sustantivos o verbos monosílabos (ej: ver, voz, sol).
- Elimina palabras débiles, confusas o rebuscadas (ej: “podría”, “vociferar”, “incongruente”).
- Usa verbos activos que aporten acción (no hables "sobre" algo, cuéntalo).
- Incluye emojis moderadamente, solo cuando refuercen la idea o capten atención.
- Siempre identifica y destaca la idea principal, con frases tipo:
  "Si hay una idea que quiero que recuerdes, es..."

📌 Frase inicial (crítica):
- La primera frase es la única oportunidad de enganchar. Para eso:
  • Concéntrate en lo más importante.
  • Evita cualquier anécdota o frase de contexto larga.
  • Limítala a una sola frase fuerte.
  • No repitas esa misma frase al final.
  • Elimina adverbios y palabras innecesarias.

🧱 Axiomas y recursos útiles:
Usa frases de apoyo potentes como:
"El contexto", "¿Y ahora qué?", "En resumen", "El trasfondo", "Conclusión", "En cifras", "Qué estamos viendo", etc.  
Estas estructuran el mensaje y dan fuerza a la idea central.

Tu misión es ayudar a decidir y entender con velocidad. Todo lo que se aleje de eso, estorba.

Documento:

"""

# Configuración de la página
st.set_page_config(
    page_title="ClariFi",
    page_icon=":brain:",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.logo('logo.png', size="large")

# CSS personalizado
st.markdown("""
<style>
    .stChatMessage {
        font-size: 1rem;
        line-height: 1.6;
    }
    .stChatMessage .stMarkdown {
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

# Función para convertir Excel a texto
def df_to_context(excel_data):
    context = "📄 Datos financieros extraídos del archivo:\n\n"
    for sheet_name, df in excel_data.items():
        context += f"🗂 Hoja: {sheet_name}\n"
        context += f"Columnas: {', '.join(str(col) for col in df.columns)}\n"
        context += f"Filas: {len(df)}\n"
        context += df.to_string(index=False)
        context += "\n\n"
    return context

# Función para leer Excel
def process_excel_file(uploaded_file):
    try:
        excel_data = pd.read_excel(uploaded_file, sheet_name=None)
        return excel_data
    except Exception as e:
        st.error(f"Error procesando el archivo: {str(e)}")
        return None

def obtener_respuesta(pregunta, excel_context=None):
    prompt = instructions
    if excel_context:
        prompt += "\nInformación financiera:\n" + excel_context
    prompt += "\n\nUsuario: " + pregunta

    # Crear instancia del modelo Gemini
    model = genai.GenerativeModel("gemini-2.5-pro")

    # Llamada a la API
    response = model.generate_content(prompt)

    return response.text.strip()

# UI principal
st.title("ClariFi")
st.markdown("Tu asistente financiero personal para emprendedores y dueños de negocios.")

# Subida del archivo
st.sidebar.header("📁 Sube tu archivo financiero")
uploaded_file = st.sidebar.file_uploader("Selecciona un archivo Excel (.xlsx)", type=["xlsx"])

# Estado del archivo
excel_data = None
excel_context = None

if uploaded_file is not None:
    excel_data = process_excel_file(uploaded_file)
    if excel_data:
        excel_context = df_to_context(excel_data)
        st.sidebar.success("✅ Archivo procesado correctamente.")

# Inicializar historial de chat si no existe
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Mostrar el historial de conversación
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Entrada del usuario
user_input = st.chat_input("💬 Escribe tu pregunta financiera aquí...")

if user_input:
    # Mostrar entrada del usuario
    st.chat_message("user").markdown(user_input)
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    
    # Generar respuesta del asistente
    response = obtener_respuesta(user_input, excel_context)
    st.chat_message("assistant").markdown(response)
    st.session_state.chat_history.append({"role": "assistant", "content": response})