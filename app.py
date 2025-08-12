import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración API - Vercel usa variables de entorno automáticamente
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("⚠️ **Error de configuración**: No se encontró GOOGLE_API_KEY")
    st.info("""
    **Para resolver este error en desarrollo:**
    1. Crea un archivo `.env` en la carpeta del proyecto
    2. Agrega esta línea: `GOOGLE_API_KEY=tu_clave_aqui`
    3. Reinicia la aplicación
    
    **Para resolver en producción (Vercel):**
    1. Ve a tu dashboard de Vercel
    2. Configura la variable de entorno GOOGLE_API_KEY
    """)
    st.stop()

genai.configure(api_key=api_key)

# ------------------- GESTIÓN DE USUARIOS -------------------
USERS_FILE = "users.json"

def load_users():
    """Cargar usuarios desde archivo JSON"""
    if Path(USERS_FILE).exists():
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Guardar usuarios en archivo JSON"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def hash_password(password):
    """Generar hash de contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email, password, profile):
    """Crear nuevo usuario"""
    users = load_users()
    if email in users:
        return False, "El usuario ya existe"
    
    users[email] = {
        "password": hash_password(password),
        "profile": profile,
        "created_at": str(pd.Timestamp.now())
    }
    save_users(users)
    return True, "Usuario creado exitosamente"

def authenticate_user(email, password):
    """Autenticar usuario"""
    users = load_users()
    if email not in users:
        return False, None
    
    if users[email]["password"] == hash_password(password):
        return True, users[email]["profile"]
    return False, None

def get_user_profile(email):
    """Obtener perfil de usuario"""
    users = load_users()
    return users.get(email, {}).get("profile", {})

def update_user_profile(email, profile):
    """Actualizar perfil de usuario"""
    users = load_users()
    if email in users:
        users[email]["profile"] = profile
        save_users(users)
        return True
    return False

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
        result = []
        
        for name, df in excel_data.items():
            # Información básica de la hoja
            result.append(f"\n=== HOJA: {name} ===")
            result.append(f"Total filas: {len(df)} | Columnas: {len(df.columns)}")
            result.append(f"Columnas: {', '.join(map(str, df.columns))}")
            
            # Filtrar filas que no estén completamente vacías
            df_clean = df.dropna(how='all')  # Eliminar filas completamente vacías
            filas_con_datos = len(df_clean)
            filas_vacias = len(df) - filas_con_datos
            
            result.append(f"Filas con datos: {filas_con_datos} | Filas vacías: {filas_vacias}")
            
            # Contenido de los datos (primeras 200 filas con datos)
            if filas_con_datos > 0:
                result.append(f"\nPRIMERAS {min(200, filas_con_datos)} FILAS CON DATOS:")
                
                # Tomar las primeras 200 filas que tengan al menos algún dato
                df_preview = df_clean.head(200)
                
                # Convertir a string y limitar caracteres para no sobrecargar
                df_string = df_preview.to_string(index=False, max_cols=20)
                if len(df_string) > 8000:  # Límite más alto para 200 filas
                    df_string = df_string[:8000] + "... [datos truncados]"
                
                result.append(df_string)
            else:
                result.append("\nEsta hoja no contiene datos válidos.")
            
            result.append("-" * 80)
        
        return "\n".join(result)
        
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
    "authenticated": False,
    "current_user": None,
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
    
    if st.button("Siguiente ➡️", use_container_width=True, key=f"onboarding_step_{step}"):
        st.session_state.user_profile[key] = value
        if step + 1 < len(steps):
            st.session_state.onboarding_step += 1
            st.rerun()
        else:
            # Guardar perfil en base de datos
            update_user_profile(st.session_state.current_user, st.session_state.user_profile)
            st.session_state.onboarding_completed = True
            st.rerun()

# ------------------- AUTENTICACIÓN -------------------
def show_auth():
    tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
    
    with tab1:
        st.subheader("Iniciar Sesión")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Contraseña", type="password", key="login_password")
        
        if st.button("Iniciar Sesión", use_container_width=True, key="login_btn"):
            if email and password:
                auth_success, profile = authenticate_user(email, password)
                if auth_success:
                    st.session_state.authenticated = True
                    st.session_state.current_user = email
                    st.session_state.user_profile = profile
                    st.session_state.onboarding_completed = bool(profile)
                    st.success("Sesión iniciada correctamente")
                    st.rerun()
                else:
                    st.error("Email o contraseña incorrectos")
            else:
                st.error("Por favor completa todos los campos")
    
    with tab2:
        st.subheader("Crear Cuenta")
        new_email = st.text_input("Email", key="register_email")
        new_password = st.text_input("Contraseña", type="password", key="register_password")
        confirm_password = st.text_input("Confirmar Contraseña", type="password", key="confirm_password")
        
        if st.button("Registrarse", use_container_width=True, key="register_btn"):
            if new_email and new_password and confirm_password:
                if new_password != confirm_password:
                    st.error("Las contraseñas no coinciden")
                elif len(new_password) < 6:
                    st.error("La contraseña debe tener al menos 6 caracteres")
                else:
                    success, message = create_user(new_email, new_password, {})
                    if success:
                        # Auto-login después del registro
                        st.session_state.authenticated = True
                        st.session_state.current_user = new_email
                        st.session_state.user_profile = {}
                        st.session_state.onboarding_completed = False
                        st.success("¡Cuenta creada! Ahora completa tu perfil")
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.error("Por favor completa todos los campos")

# ------------------- INTERFAZ -------------------
st.title(":brain: Finni")
st.markdown("Asistente financiero para emprendedores y dueños de negocios.")

if not st.session_state.authenticated:
    show_auth()
elif not st.session_state.onboarding_completed:
    st.subheader(f"¡Bienvenido {st.session_state.current_user}!")
    st.markdown("Completa tu perfil para personalizar tu experiencia")
    show_onboarding()
else:
    # Sidebar perfil y logout
    with st.sidebar:
        st.subheader(f"👋 {st.session_state.current_user}")
        if st.button("Cerrar Sesión", key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.session_state.user_profile = {}
            st.session_state.chat_history = []
            st.session_state.onboarding_step = 0
            st.session_state.onboarding_completed = False
            st.rerun()
        
        st.markdown("---")
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
