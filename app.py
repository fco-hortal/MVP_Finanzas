import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# Configuración API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ------------------- DATOS SECTORIALES -------------------
conocimiento_sectorial = {
    "Agricultura": "Paltas, cerezas, mandarinas. Factores: tipo de cambio, riego, mano de obra, fletes. Métricas: ton/ha, precio/kg, merma. Riesgos: sequía, plagas. Oportunidades: certificaciones, valor agregado.",
    "Cafeterías": "Demanda: mañana/tarde. Costos: arriendo, insumos, personal. Métricas: ticket promedio, margen por producto. Estrategias: combos, fidelización.",
    "Diálisis": "Demanda creciente. Costos: insumos, equipos, personal. Métricas: ingreso por sesión, ocupación. Riesgos: insumos importados, licitaciones. Oportunidades: expansión, convenios.",
    "Legaltech": "Modelo SaaS/caso. Costos: desarrollo, abogados, marketing. Métricas: MRR, CAC, churn. Riesgos: adopción lenta. Oportunidades: automatización, nichos.",
    "Packaging": "Demanda: agro, retail, e-commerce. Costos: cartón, energía, personal. Métricas: costo/unidad, desperdicio. Oportunidades: sustentabilidad, personalización.",
    "Otro": "Industria no especificada."
}

# ------------------- PROMPT -------------------
def construir_prompt(industria, perfil_usuario, excel_context, pregunta):
    sector = conocimiento_sectorial.get(industria, conocimiento_sectorial["Otro"])
    perfil_texto = "\n".join(f"- {k}: {v}" for k, v in perfil_usuario.items())
    
    return f"""
Eres Finni, asistente financiero en Chile. Responde claro, breve y con pasos accionables.

Industria: {industria}
Sector info: {sector}
Perfil usuario:
{perfil_texto}

Datos financieros:
{excel_context or 'No hay archivo cargado'}

Pregunta:
{pregunta}
"""

# ------------------- FUNCIONES -------------------
def process_excel_file(uploaded_file):
    try:
        excel_data = pd.read_excel(uploaded_file, sheet_name=None)
        return "\n".join(f"Hoja: {name} | Columnas: {', '.join(map(str, df.columns))} | Filas: {len(df)}"
                         for name, df in excel_data.items())
    except Exception as e:
        st.error(f"Error procesando el archivo: {str(e)}")
        return None

def obtener_respuesta(pregunta, excel_context):
    industria = st.session_state.user_profile.get("industria", "Otro")
    prompt = construir_prompt(industria, st.session_state.user_profile, excel_context, pregunta)
    
    model = genai.GenerativeModel("gemini-2.5-pro")
    resp = model.generate_content(prompt)
    return resp.text.strip()

# ------------------- CONFIG PÁGINA -------------------
st.set_page_config(page_title="Finni", page_icon=":brain:", layout="centered")

# ------------------- ESTADO -------------------
for key, val in {
    "onboarding_step": 0,
    "onboarding_completed": False,
    "user_profile": {},
    "chat_history": []
}.items():
    st.session_state.setdefault(key, val)

# ------------------- ONBOARDING -------------------
def show_onboarding():
    steps = [
        ("Industria", list(conocimiento_sectorial.keys()), "industria"),
        ("Estado del negocio", ["Incipiente", "Madura", "En transición", "No lo tengo claro"], "estado_industria"),
        ("Tipo de negocio", ["Startup tecnológica", "Negocio tradicional", "Empresa en expansión", "Emprendimiento unipersonal", "Otro"], "tipo_negocio"),
        ("Rol", ["CEO/Fundador", "Director(a)", "Gerente/Administrador(a)", "Dueño(a)", "Otro"], "rol"),
        ("Objetivo principal", ["Mejorar flujo de caja", "Detectar riesgos y oportunidades", "Planificar crecimiento", "Optimizar gastos", "Tener claridad de mis números"], "objetivo_principal"),
        ("Dolor principal", ["No sé por dónde empezar", "No tengo claro mis números", "Quiero vender más", "Estoy perdiendo plata", "Otro"], "dolor_principal")
    ]
    
    step = st.session_state.onboarding_step
    titulo, opciones, key = steps[step]
    
    st.subheader(f"Paso {step+1}/{len(steps)}: {titulo}")
    value = st.radio("Selecciona una opción:", opciones)
    
    if st.button("Siguiente ➡️", use_container_width=True):
        st.session_state.user_profile[key] = value
        if step + 1 < len(steps):
            st.session_state.onboarding_step += 1
        else:
            st.session_state.onboarding_completed = True

# ------------------- INTERFAZ -------------------
st.title(":brain: Finni")
st.markdown("Asistente financiero para emprendedores y dueños de negocios.")

if not st.session_state.onboarding_completed:
    show_onboarding()
else:
    # Sidebar perfil
    with st.sidebar:
        st.subheader("🎯 Tu Perfil")
        for k, v in st.session_state.user_profile.items():
            st.markdown(f"**{k.capitalize()}**: {v}")
        
        st.markdown("---")
        st.subheader("📁 Sube archivo financiero")
        uploaded_file = st.file_uploader("Excel (.xlsx)", type=["xlsx"])
        excel_context = process_excel_file(uploaded_file) if uploaded_file else None

    # Chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    user_input = st.chat_input("💬 Escribe tu pregunta...")
    if user_input:
        st.chat_message("user").markdown(user_input)
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        respuesta = obtener_respuesta(user_input, excel_context)
        st.chat_message("assistant").markdown(respuesta)
        st.session_state.chat_history.append({"role": "assistant", "content": respuesta})
