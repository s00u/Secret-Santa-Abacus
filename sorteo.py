import random
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st

# --- CONFIGURACIÓN DEL CORREO EMISOR ---
# Nota: Si usas Gmail, necesitas generar una "Contraseña de Aplicación" en tu cuenta de Google.
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
SENDER_PASSWORD = st.secrets["SENDER_PASSWORD"]


# --- CONFIGURACIÓN DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect("intercambio.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS participantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            deseos TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resultados (
            remitente_email TEXT PRIMARY KEY,
            destinatario_nombre TEXT,
            destinatario_deseos TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- FUNCIONES DE LÓGICA ---
def enviar_correo(to_email, nombre_remitente, nombre_asignado, deseos_asignado):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg['Subject'] = "¡Resultado del Sorteo de Intercambio!"

    cuerpo = f"""
    ¡Hola, {nombre_remitente}!
    
    El sorteo se ha realizado con éxito. 
    Te tocó regalarle a: **{nombre_asignado}**
    
    Su lista de deseos es:
    {deseos_asignado if deseos_asignado else "No especificó ninguna lista de deseos."}
    
    ¡Felices fiestas y buena suerte con el regalo! 🎄✨
    """
    msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Error al enviar correo a {to_email}: {e}")
        return False

def realizar_sorteo():
    conn = sqlite3.connect("intercambio.db")
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, email, deseos FROM participantes")
    participantes = cursor.fetchall()
    
    if len(participantes) < 2:
        st.warning("Se necesitan al menos 2 participantes para realizar el sorteo.")
        conn.close()
        return

    # Algoritmo de Derivación (Derangement) para que nadie se toque a sí mismo
    personajes = participantes.copy()
    while True:
        random.shuffle(personajes)
        if all(participantes[i][1] != personajes[i][1] for i in range(len(participantes))):
            break

    # Guardar resultados y enviar correos
    cursor.execute("DELETE FROM resultados")
    exito_total = True
    
    for i in range(len(participantes)):
        remitente_nombre, remitente_email, _ = participantes[i]
        asignado_nombre, asignado_email, asignado_deseos = personajes[i]
        
        cursor.execute(
            "INSERT INTO resultados VALUES (?, ?, ?)",
            (remitente_email, asignado_nombre, asignado_deseos)
        )
        
        # Enviar la notificación
        enviado = enviar_correo(remitente_email, remitente_nombre, asignado_nombre, asignado_deseos)
        if not enviado:
            exito_total = False

    conn.commit()
    conn.close()
    
    if exito_total:
        st.success("¡El sorteo se realizó con éxito y todos los correos fueron enviados!")
    else:
        st.warning("El sorteo terminó, pero hubo problemas al enviar algunos correos.")

# --- INTERFAZ DE USUARIO (STREAMLIT) ---
st.title("Organizador de Intercambios (Amigo Secreto)")

tab1, tab2 = st.tabs(["Registrar Participante", "Panel del Administrador"])

with tab1:
    st.header("Únete al intercambio")
    with st.form("registro_form", clear_on_submit=True):
        nombre = st.text_input("Tu Nombre Completo:")
        email = st.text_input("Tu Correo Electrónico:")
        deseos = st.text_area("Tu Lista de Deseos (¿Qué te gustaría recibir?):")
        submit = st.form_submit_button("Registrarme")
        
        if submit:
            if nombre and email:
                try:
                    conn = sqlite3.connect("intercambio.db")
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO participantes (nombre, email, deseos) VALUES (?, ?, ?)", (nombre, email, deseos))
                    conn.commit()
                    conn.close()
                    st.success(f"¡{nombre} ha sido registrado exitosamente!")
                except sqlite3.IntegrityError:
                    st.error("Este correo electrónico ya está registrado.")
            else:
                st.error("Por favor, llena los campos obligatorios (Nombre y Correo).")

with tab2:
    st.header("Control del Sorteo")
    
    conn = sqlite3.connect("intercambio.db")
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, email, deseos FROM participantes")
    lista_participantes = cursor.fetchall()
    conn.close()
    
    st.subheader(f"Participantes actuales ({len(lista_participantes)})")
    for p in lista_participantes:
        st.text(f"• {p[0]} ({p[1]}) - Deseos: {p[2][:30]}...")

    st.write("---")
    if st.button("¡REALIZAR SORTEO Y NOTIFICAR POR CORREO!", type="primary"):
        with st.spinner("Realizando combinaciones secretas y enviando correos..."):
            realizar_sorteo()
