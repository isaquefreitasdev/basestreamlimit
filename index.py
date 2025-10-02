import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
import os
import io
import time
import json

# -----------------------------
# CONFIGURAÇÕES INICIAIS
# -----------------------------
USER_FILE = "users.json"
ADMIN_USER = "admin"
ADMIN_PASS = "123456"  # ⚠️ Troque a senha de admin!

st.set_page_config(page_title="Manual do Trade - Fortali", layout="centered")

if not os.path.exists("pdfs"):
    os.makedirs("pdfs")

# -----------------------------
# ESTADO INICIAL
# -----------------------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_level' not in st.session_state:
    st.session_state.user_level = 0
if 'selected_pdf' not in st.session_state:
    st.session_state.selected_pdf = None
if 'search_input_primary' not in st.session_state:
    st.session_state.search_input_primary = ""

# -----------------------------
# FUNÇÕES DE USUÁRIOS
# -----------------------------
def load_users():
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.error("Erro ao ler o arquivo de usuários. JSON inválido.")
            return {ADMIN_USER: {"password": ADMIN_PASS, "level": 3}}
    else:
        initial_users = {ADMIN_USER: {"password": ADMIN_PASS, "level": 3}}
        save_users(initial_users)
        return initial_users

def save_users(users_data):
    with open(USER_FILE, 'w') as f:
        json.dump(users_data, f, indent=4)

if 'user_db' not in st.session_state:
    st.session_state.user_db = load_users()
else:
    st.session_state.user_db = load_users()

# -----------------------------
# FUNÇÕES DE DOCUMENTOS
# -----------------------------
def load_documents_from_disk():
    documents = []
    for filename in os.listdir("pdfs"):
        if filename.endswith(".pdf"):
            processo_nome_raw = os.path.splitext(filename)[0]
            parts = processo_nome_raw.split('_')
            if parts and parts[-1].isdigit():
                processo_name_parts = parts[:-1]
            else:
                processo_name_parts = parts
            processo_nome_display = ' '.join(word.capitalize() for word in processo_name_parts)
            if not processo_nome_display.strip():
                processo_nome_display = filename
            documents.append({"processo": processo_nome_display, "arquivo": os.path.join("pdfs", filename)})
    documents.sort(key=lambda d: d['processo'])
    return documents

if 'documentos' not in st.session_state:
    st.session_state.documentos = load_documents_from_disk()

def select_pdf(arquivo_path):
    if not arquivo_path or not isinstance(arquivo_path, str):
        st.session_state.selected_pdf = None
        return
    if not os.path.exists(arquivo_path):
        st.error(f"Erro: O arquivo '{arquivo_path}' não foi encontrado.")
        st.session_state.selected_pdf = None
    else:
        st.session_state.selected_pdf = arquivo_path

def save_uploaded_file(uploaded_file, processo_nome):
    file_extension = uploaded_file.name.split('.')[-1]
    safe_name_base = processo_nome.replace(' ', '_').lower()
    unique_suffix = str(int(time.time()))[-6:]
    safe_name = f"{safe_name_base}_{unique_suffix}.{file_extension}"
    file_path = os.path.join("pdfs", safe_name)
    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state.documentos = load_documents_from_disk()
        st.success(f"Documento '{processo_nome}' salvo e atualizado na lista!")
    except Exception as e:
        st.error(f"Falha ao salvar o arquivo: {e}")

def delete_document(documento):
    try:
        os.remove(documento["arquivo"])
        st.session_state.documentos = load_documents_from_disk()
        st.session_state.selected_pdf = None
        st.success(f"Documento '{documento['processo']}' removido com sucesso!")
        st.rerun()
    except OSError as e:
        st.error(f"Erro ao tentar remover o arquivo: {e}")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")

# -----------------------------
# FUNÇÕES DE LOGIN
# -----------------------------
def login_form():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>🔒 Login de Acesso</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")
            if submitted:
                st.session_state.user_db = load_users()
                if username in st.session_state.user_db and st.session_state.user_db[username]["password"] == password:
                    st.session_state.authenticated = True
                    st.session_state.user_level = st.session_state.user_db[username]["level"]
                    st.success(f"Bem-vindo(a), {username}!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

def logout_button_center():
    st.button(
        "Sair",
        on_click=lambda: st.session_state.update(
            authenticated=False,
            user_level=0,
            selected_pdf=None,
            search_input_primary=""
        )
    )

def check_permission(required_level):
    return st.session_state.user_level >= required_level

# -----------------------------
# FUNÇÃO DE PESQUISA DINÂMICA
# -----------------------------
def render_search_page():
    st.write("### Digite o processo que deseja consultar:")

    termo = st.text_input(
        "Pesquisar processo",
        value=st.session_state.search_input_primary,
        key="search_input_primary"
    )

    documentos = st.session_state.documentos

    if termo.strip():
        resultados = [d for d in documentos if termo.lower() in d["processo"].lower()]
    else:
        resultados = []

    st.write("---")

    if resultados:
        st.markdown("#### 📖 Processos encontrados:")
        for r in resultados:
            st.button(
                r["processo"],
                key=f"search_btn_{r['processo']}",
                on_click=select_pdf,
                args=[r["arquivo"]]
            )
    elif termo.strip():
        st.warning(f"Nenhum resultado encontrado para '{termo}'.")
    else:
        st.info("Digite um termo para pesquisar ou use a aba 'Visualizar Todos'.")

# -----------------------------
# FUNÇÕES DE VISUALIZAÇÃO, UPLOAD E ADMIN
# -----------------------------
def render_all_documents_page():
    st.markdown("### Lista Completa de Documentos")
    documentos = st.session_state.documentos

    # Upload (nível 2+)
    if check_permission(2):
        with st.expander("➕ Adicionar Novo Documento", expanded=False):
            with st.form("upload_form_tab2", clear_on_submit=True):
                new_processo_nome = st.text_input("Nome do Processo/Documento", key="new_nome_tab2")
                uploaded_file = st.file_uploader("Selecione o arquivo PDF", type=["pdf"], key="new_file_tab2")
                submitted = st.form_submit_button("Salvar Documento")
                if submitted:
                    if new_processo_nome and uploaded_file:
                        save_uploaded_file(uploaded_file, new_processo_nome)
                    else:
                        st.warning("Preencha todos os campos.")

    st.write("---")

    if documentos:
        # Remoção (nível 3)
        if check_permission(3):
            st.markdown("#### 🗑️ Documentos Cadastrados (Clique para Remover)")
            cols = st.columns(3)
            for i, r in enumerate(documentos):
                col = cols[i % 3]
                col.button(f"🗑️ {r['processo']}", key=f"del_{i}", on_click=delete_document, args=[r])

        # Visualização (nível 1+)
        st.markdown("#### 📖 Clique no Processo para Visualizar")
        for r in documentos:
            st.button(r["processo"], on_click=select_pdf, args=[r["arquivo"]], key=f"all_btn_{r['processo']}")
    else:
        st.warning("Nenhum documento cadastrado na pasta 'pdfs'.")

def render_admin_page():
    st.markdown("### Criação e Gerenciamento de Acessos")
    if check_permission(3):
        # Novo usuário
        st.markdown("#### Novo Usuário")
        with st.form("add_user_form", clear_on_submit=True):
            new_username = st.text_input("Nome de Usuário (login)", key="new_user").lower()
            new_password = st.text_input("Senha Inicial", type="password", key="new_pass")
            new_level = st.selectbox(
                "Nível de Acesso",
                options=["Consulta (1)", "Adicionar (2)", "Remoção (3)"],
                index=0,
                key="new_level_select"
            )
            level_map = {"Consulta (1)": 1, "Adicionar (2)": 2, "Remoção (3)": 3}
            submitted = st.form_submit_button("Cadastrar Usuário")
            if submitted:
                if not new_username or not new_password:
                    st.error("Preencha o usuário e a senha.")
                elif new_username in st.session_state.user_db:
                    st.error(f"O usuário '{new_username}' já existe.")
                elif level_map[new_level] == 3 and new_username != ADMIN_USER:
                    st.warning("A criação de novos super administradores é restrita.")
                else:
                    st.session_state.user_db[new_username] = {"password": new_password, "level": level_map[new_level]}
                    save_users(st.session_state.user_db)
                    st.success(f"Usuário `{new_username}` criado com sucesso (Nível {level_map[new_level]}).")
                    st.rerun()
    else:
        st.error("Acesso negado. Apenas Admin pode criar acessos.")

# -----------------------------
# EXECUÇÃO PRINCIPAL
# -----------------------------
if not st.session_state.authenticated:
    st.markdown(
        """
        <h1 style="text-align:center; color:white; background-color:#a10d28; padding:20px; border-radius:10px; margin-bottom: 30px;">
            Manual do Trade - Fortali
        </h1>
        """,
        unsafe_allow_html=True
    )
    login_form()
    st.markdown("<div style='text-align: center; margin-top: 20px;'>", unsafe_allow_html=True)
    st.info("Utilize seu usuário e senha para acessar o manual.")
    st.markdown("</div>", unsafe_allow_html=True)
else:
    logout_button_center()
    st.markdown(
        """
        <h1 style="text-align:center; color:white; background-color:#a10d28; padding:15px; border-radius:10px; margin-top: -30px;">
            Manual do Trade - Fortali
        </h1>
        <p style="text-align:center; font-style:italic; margin-top:10px; margin-bottom: 0px;">
            "Não sei fazer!", "Fulano que faz isso", "Ninguém me ensinou".
        </p>
        """,
        unsafe_allow_html=True
    )

    PAGES = ["Pesquisar Processo", "Visualizar Todos"]
    if check_permission(3):
        PAGES.append("Criação de Acessos")

    tabs = st.tabs(PAGES)
    st.markdown("---")

    if st.session_state.selected_pdf:
        st.button("↩ Voltar para o Menu", on_click=select_pdf, args=[None])
        st.write("---")
        pdf_path = st.session_state.selected_pdf
        documentos = st.session_state.documentos
        processo_nome = next((item["processo"] for item in documentos if item["arquivo"] == pdf_path), "Documento")
        st.markdown(f"## Visualizando: {processo_nome}")
        st.info("O PDF está embutido abaixo.")
        try:
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
            pdf_viewer(input=pdf_data)
            st.write("---")
            st.download_button(
                label="📥 Baixar PDF Original",
                data=pdf_data,
                file_name=pdf_path.split("/")[-1],
                mime="application/pdf"
            )
        except FileNotFoundError:
            st.error(f"Erro: O arquivo PDF em '{pdf_path}' não pôde ser encontrado.")
            st.session_state.selected_pdf = None
    else:
        with tabs[0]:
            render_search_page()
        with tabs[1]:
            render_all_documents_page()
        if len(tabs) > 2:
            with tabs[2]:
                render_admin_page()
