import os
import pandas as pd
import streamlit as st
import google.generativeai as genai
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(
    page_title="Analizador de Estados Financieros",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurar Gemini AI
try:
    genai.configure(api_key=os.getenv("API_KEY_GEMINI"))
    model = genai.GenerativeModel("gemini-1.5-flash")
except Exception as e:
    st.error("Error configurando Gemini AI. Verifica tu API_KEY_GEMINI en las variables de entorno.")

# CSS personalizado para mejorar el diseño
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .financial-table {
        font-size: 0.9rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left-color: #2196f3;
    }
    .bot-message {
        background-color: #f3e5f5;
        border-left-color: #9c27b0;
    }
</style>
""", unsafe_allow_html=True)

# Función para procesar el Excel
def process_excel_file(uploaded_file):
    """Procesa el archivo Excel y extrae la información financiera"""
    try:
        # Leer todas las hojas del Excel
        excel_data = pd.read_excel(uploaded_file, sheet_name=None)
        return excel_data
    except Exception as e:
        st.error(f"Error procesando el archivo: {str(e)}")
        return None

# Función para crear visualizaciones
def create_visualizations(df):
    """Crea gráficos basados en los datos financieros"""
    try:
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        if len(numeric_cols) >= 2:
            st.subheader("📊 Visualizaciones")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico de barras
                if len(df) <= 20:  # Solo si no hay demasiados datos
                    fig_bar = px.bar(
                        df.head(10), 
                        x=df.columns[0], 
                        y=numeric_cols[0],
                        title=f"Gráfico de Barras - {numeric_cols[0]}"
                    )
                    fig_bar.update_layout(height=400)
                    st.plotly_chart(fig_bar, use_container_width=True)
            
            with col2:
                # Gráfico de pastel si hay datos categóricos
                if len(numeric_cols) >= 1 and len(df) <= 10:
                    fig_pie = px.pie(
                        df.head(8), 
                        values=numeric_cols[0], 
                        names=df.columns[0],
                        title=f"Distribución - {numeric_cols[0]}"
                    )
                    fig_pie.update_layout(height=400)
                    st.plotly_chart(fig_pie, use_container_width=True)
                    
    except Exception as e:
        st.info("No se pudieron generar visualizaciones automáticas")

# Función para el chatbot
def get_ai_response(question, data_context):
    """Genera respuesta usando Gemini AI"""
    try:
        prompt = f"""
        Eres un asistente financiero experto. Tienes acceso a los siguientes datos financieros:
        
        {data_context}
        
        Pregunta del usuario: {question}
        
        Por favor, proporciona una respuesta detallada y profesional basada en los datos disponibles. 
        Si la pregunta no se puede responder con los datos proporcionados, indica qué información adicional sería necesaria.
        Responde en español de manera clara y concisa.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generando respuesta: {str(e)}"

def df_to_context(excel_data):
    """Convierte los datos del Excel en un contexto de texto completo para el AI."""
    context = "Datos financieros disponibles:\n\n"

    for sheet_name, df in excel_data.items():
        context += f"Hoja: {sheet_name}\n"
        context += f"Columnas: {', '.join(str(col) for col in df.columns)}\n"
        context += f"Número de filas: {len(df)}\n"
        context += "Contenido:\n"
        df_str = df.to_string(index=False)
        context += df_str
        context += "\n\n"
    return context


# Sidebar para navegación
st.sidebar.title("🏦 Navegación")
page = st.sidebar.radio("Selecciona una página:", ["📊 Dashboard Financiero", "🤖 Chatbot Financiero"])

# Inicializar session state
if 'excel_data' not in st.session_state:
    st.session_state.excel_data = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Página principal - Dashboard
if page == "📊 Dashboard Financiero":
    st.markdown('<h1 class="main-header">Dashboard de Estado Financiero</h1>', unsafe_allow_html=True)
    
    # Subir archivo
    uploaded_file = st.file_uploader(
        "📁 Sube tu archivo Excel con el estado financiero",
        type=['xlsx', 'xls'],
        help="Formatos soportados: .xlsx, .xls"
    )
    
    if uploaded_file is not None:
        # Procesar archivo
        with st.spinner('Procesando archivo...'):
            excel_data = process_excel_file(uploaded_file)
            
        if excel_data:
            st.session_state.excel_data = excel_data
            st.success("✅ Archivo cargado exitosamente!")
            
            # Mostrar información general
            st.subheader("📋 Información General del Archivo")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.info(f"**Nombre:** {uploaded_file.name}")
            with col2:
                st.info(f"**Hojas:** {len(excel_data)}")
            with col3:
                total_rows = sum(len(df) for df in excel_data.values())
                st.info(f"**Total Filas:** {total_rows}")
            
            # Selector de hoja
            sheet_names = list(excel_data.keys())
            selected_sheet = st.selectbox("Selecciona la hoja a visualizar:", sheet_names)
            
            if selected_sheet:
                df = excel_data[selected_sheet]
                
                # Mostrar tabla
                st.subheader(f"📊 Datos de la Hoja: {selected_sheet}")
                st.dataframe(df, use_container_width=True)
                
                # Crear visualizaciones
                create_visualizations(df)

# Página del Chatbot
elif page == "🤖 Chatbot Financiero":
    st.markdown('<h1 class="main-header">Chatbot Financiero</h1>', unsafe_allow_html=True)
    
    if st.session_state.excel_data is None:
        st.warning("⚠️ Por favor, primero carga un archivo Excel en el Dashboard Financiero.")
        if st.button("Ir al Dashboard"):
            st.rerun()
    else:
        st.success("✅ Datos financieros cargados. ¡Haz tus preguntas!")
        
        # Mostrar historial de chat
        st.subheader("💬 Conversación")
        
        # Contenedor para el chat
        chat_container = st.container()
        
        with chat_container:
            for i, (user_msg, bot_msg) in enumerate(st.session_state.chat_history):
                # Mensaje del usuario
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>🙋 Tú:</strong> {user_msg}
                </div>
                """, unsafe_allow_html=True)
                
                # Respuesta del bot
                st.markdown(f"""
                <div class="chat-message bot-message">
                    <strong>🤖 Asistente:</strong> {bot_msg}
                </div>
                """, unsafe_allow_html=True)
        
        # Input para nueva pregunta
        st.subheader("❓ Haz una pregunta sobre tus datos financieros")
        
        user_question = st.text_input(
            "Tu pregunta:",
            placeholder="Ej: ¿Cuáles son los ingresos totales? ¿Cómo está la rentabilidad?",
            key="user_input"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Enviar", type="primary"):
                if user_question.strip():
                    with st.spinner('Analizando datos...'):
                        # Convertir datos a contexto
                        data_context = df_to_context(st.session_state.excel_data)
                        
                        # Obtener respuesta del AI
                        ai_response = get_ai_response(user_question, data_context)
                        
                        # Agregar al historial
                        st.session_state.chat_history.append((user_question, ai_response))
                        
                        st.rerun()
                else:
                    st.warning("Por favor, escribe una pregunta.")
        
        with col2:
            if st.button("Limpiar Chat"):
                st.session_state.chat_history = []
                st.rerun()
        
        # Sugerencias de preguntas
        st.subheader("💡 Preguntas Sugeridas")
        suggestions = [
            "¿Cuál es el resumen de los ingresos y gastos?",
            "¿Cómo está la situación de liquidez?",
            "¿Cuáles son las principales categorías de gastos?",
            "¿Hay alguna tendencia preocupante en los datos?",
            "¿Qué recomendaciones financieras puedes darme?"
        ]
        
        cols = st.columns(2)
        for i, suggestion in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(suggestion, key=f"suggestion_{i}"):
                    # Simular click con la sugerencia
                    with st.spinner('Analizando datos...'):
                        data_context = df_to_context(st.session_state.excel_data)
                        ai_response = get_ai_response(suggestion, data_context)
                        st.session_state.chat_history.append((suggestion, ai_response))
                        st.rerun()

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("🔧 **Desarrollado con Streamlit y Gemini AI**")
st.sidebar.markdown("📊 **Versión 1.0**")