import streamlit as st
import sqlite3
import datetime
import pandas as pd
import hashlib
import math

# Configuração da Página
st.set_page_config(page_title="Repeat It - SM-2", layout="centered")

# -----------------------------------------------------------------------------
# ESTADO DA SESSÃO
# -----------------------------------------------------------------------------
if "usuario" not in st.session_state:
    st.session_state.usuario = None  
if "clique_offset" not in st.session_state:
    st.session_state.clique_offset = 0  
if "data_selecionada" not in st.session_state:
    # Novo formato de data padronizado no app inteiro
    st.session_state.data_selecionada = datetime.date.today().strftime("%d/%m/%Y")

# -----------------------------------------------------------------------------
# BANCO DE DADOS (SQLite)
# -----------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect("revisoes.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            usuario TEXT PRIMARY KEY,
            senha TEXT
        )
    """)
    
    # Tabela v4 com formato de data DD/MM/YYYY
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questoes_sm2_v4 (
            id_questao TEXT,
            usuario TEXT,
            total_tentativas INTEGER,
            sequencia_retencao INTEGER,
            fator_facilidade REAL,
            intervalo INTEGER,
            ultima_dificuldade INTEGER,
            proxima_revisao TEXT,
            PRIMARY KEY (id_questao, usuario)
        )
    """)
    conn.commit()
    conn.close()

def query_db(query, params=(), fetchall=True):
    conn = sqlite3.connect("revisoes.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchall() if fetchall else cursor.fetchone()
    conn.commit()
    conn.close()
    return res

init_db()

def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# -----------------------------------------------------------------------------
# TELA DE AUTENTICAÇÃO
# -----------------------------------------------------------------------------
if st.session_state.usuario is None:
    st.title("Repeat It 🧠")
    st.caption("Gerenciador Adaptativo (SuperMemo SM-2)")
    
    tab_login, tab_cadastrar = st.tabs(["🔒 Entrar", "📝 Criar Conta"])
    
    with tab_login:
        st.subheader("Acessar sua Conta")
        with st.form("form_login"):
            user_login = st.text_input("Usuário:", key="login_user").strip().lower()
            senha_login = st.text_input("Senha:", type="password", key="login_pass")
            botao_login = st.form_submit_button("Entrar", use_container_width=True)
            
            if botao_login:
                if user_login and senha_login:
                    busca_user = query_db("SELECT senha FROM usuarios WHERE usuario = ?", (user_login,), fetchall=False)
                    
                    if not busca_user:
                        st.error("❌ Usuário não existe.")
                    elif busca_user[0] != criptografar_senha(senha_login):
                        st.error("❌ Senha incorreta.")
                    else:
                        st.session_state.usuario = user_login
                        st.rerun()
                else:
                    st.warning("Por favor, preencha todos os campos.")
                    
    with tab_cadastrar:
        st.subheader("Cadastrar Novo Usuário")
        user_cad = st.text_input("Escolha um nome de usuário único:", key="cad_user").strip().lower()
        
        usuario_valido = False
        if user_cad:
            usuario_existe = query_db("SELECT 1 FROM usuarios WHERE usuario = ?", (user_cad,), fetchall=False)
            if usuario_existe:
                st.error(f"❌ O usuário `{user_cad}` já está em uso.")
            else:
                st.success(f"✅ O usuário `{user_cad}` está disponível!")
                usuario_valido = True
                
        senha_cad = st.text_input("Escolha uma senha forte:", type="password", key="cad_pass")
        senha_cad_conf = st.text_input("Confirme sua senha:", type="password", key="cad_pass_conf")
        botao_cadastro = st.button("Criar Conta", use_container_width=True)
        
        if botao_cadastro:
            if user_cad and senha_cad and senha_cad_conf:
                if not usuario_valido:
                    st.error("Corrija o nome de usuário antes de continuar.")
                elif senha_cad != senha_cad_conf:
                    st.error("As senhas informadas não coincidem.")
                elif len(senha_cad) < 6:
                    st.error("A senha deve ter pelo menos 6 caracteres.")
                else:
                    senha_hash = criptografar_senha(senha_cad)
                    query_db("INSERT INTO usuarios (usuario, senha) VALUES (?, ?)", (user_cad, senha_hash))
                    st.success("🎉 Conta criada com sucesso! Mude para a aba 'Entrar' para fazer o login.")
            else:
                st.warning("Preencha todos os campos para efetuar o cadastro.")
    st.stop()

# -----------------------------------------------------------------------------
# ALGORITMO SUPERMEMO 2 (SM-2)
# -----------------------------------------------------------------------------
def calcular_sm2(dificuldade_usuario, sequencia_retencao, fator_facilidade, intervalo):
    q = 5 - dificuldade_usuario
    
    if q >= 3:
        if sequencia_retencao == 0:
            novo_intervalo = 1
        elif sequencia_retencao == 1:
            novo_intervalo = 6
        else:
            novo_intervalo = math.ceil(intervalo * fator_facilidade)
        nova_sequencia = sequencia_retencao + 1
    else:
        nova_sequencia = 0
        novo_intervalo = 1
    
    novo_fator = fator_facilidade + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    novo_fator = max(1.3, novo_fator)
    
    return nova_sequencia, round(novo_fator, 2), novo_intervalo

def registrar_resposta_sm2(id_questao, dificuldade_usuario, questao_existente=None):
    hoje = datetime.date.today()
    
    if not questao_existente:
        total_tentativas, sequencia_retencao, fator_facilidade, intervalo = 0, 0, 2.5, 0
    else:
        total_tentativas, sequencia_retencao, fator_facilidade, intervalo = questao_existente
        
    nova_sequencia, novo_fator, novo_intervalo = calcular_sm2(dificuldade_usuario, sequencia_retencao, fator_facilidade, intervalo)
    novo_total = total_tentativas + 1
    proxima_data = hoje + datetime.timedelta(days=novo_intervalo)
    
    query_db(
        """INSERT OR REPLACE INTO questoes_sm2_v4 
           (id_questao, usuario, total_tentativas, sequencia_retencao, fator_facilidade, intervalo, ultima_dificuldade, proxima_revisao) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (id_questao, st.session_state.usuario, novo_total, nova_sequencia, novo_fator, novo_intervalo, dificuldade_usuario, proxima_data.strftime("%d/%m/%Y"))
    )

# -----------------------------------------------------------------------------
# ESCALA DE AVALIAÇÃO
# -----------------------------------------------------------------------------
ESCALA_DIFICULDADE = {
    5: "5️⃣ Nunca nem vi",
    4: "4️⃣ Já ouvi falar (e só)",
    3: "3️⃣ Hardcore",
    2: "2️⃣ Fiquei na dúvida",
    1: "1️⃣ Hesitei",
    0: "0️⃣ Molezinha"
}

# -----------------------------------------------------------------------------
# POPUP DE CONFIRMAÇÃO DIALOG (Modificação Manual)
# -----------------------------------------------------------------------------
@st.dialog("Confirmar Alteração de Data")
def confirmar_alteracao_dialog(id_q, data_antiga, data_nova):
    st.warning(f"⚠️ Você está prestes a mudar o cronograma da questão: **{id_q}**")
    st.markdown(f"**Data Antiga:** `{data_antiga}`")
    st.markdown(f"**Nova Data:** `{data_nova.strftime('%d/%m/%Y')}`")
    
    col_sim, col_nao = st.columns(2)
    if col_sim.button("Sim, tenho certeza", use_container_width=True, type="primary"):
        query_db(
            "UPDATE questoes_sm2_v4 SET proxima_revisao = ? WHERE id_questao = ? AND usuario = ?", 
            (data_nova.strftime("%d/%m/%Y"), id_q, st.session_state.usuario)
        )
        st.rerun()
    if col_nao.button("Cancelar", use_container_width=True):
        st.rerun()

# -----------------------------------------------------------------------------
# INTERFACE PRINCIPAL
# -----------------------------------------------------------------------------
col_titulo, col_logout = st.columns([4, 1])
with col_titulo:
    st.title("Repeat It 🧠")
    st.caption(f"Conta ativa: **{st.session_state.usuario}**")
with col_logout:
    st.write("") 
    if st.button("Sair ↩️", use_container_width=True):
        st.session_state.usuario = None
        st.rerun()

hoje_base = datetime.date.today()
hoje_str = hoje_base.strftime("%d/%m/%Y")

todos_dados_usuario = query_db(
    "SELECT id_questao, total_tentativas, sequencia_retencao, fator_facilidade, intervalo, ultima_dificuldade, proxima_revisao FROM questoes_sm2_v4 WHERE usuario = ?", 
    (st.session_state.usuario,)
)

# -----------------------------------------------------------------------------
# BARRA DE CRONOGRAMA 
# -----------------------------------------------------------------------------
st.write("")

col_prev, *cols_dias, col_next = st.columns([0.6, 1, 1, 1, 1, 1, 0.6])

with col_prev:
    st.write("")  
    if st.button("◀️", key="btn_nav_prev", use_container_width=True):
        st.session_state.clique_offset -= 5
        st.rerun()

for i, col in enumerate(cols_dias):
    data_alvo_obj = hoje_base + datetime.timedelta(days=st.session_state.clique_offset + i)
    data_alvo_str = data_alvo_obj.strftime("%d/%m/%Y")
    
    if data_alvo_str == hoje_str:
        label = "Hoje"
        qtd = sum(1 for item in todos_dados_usuario if datetime.datetime.strptime(item[6], "%d/%m/%Y").date() <= hoje_base)
    elif data_alvo_str == (hoje_base + datetime.timedelta(days=1)).strftime("%d/%m/%Y"):
        label = "Amanhã"
        qtd = sum(1 for item in todos_dados_usuario if item[6] == data_alvo_str)
    else:
        label = data_alvo_obj.strftime("%d/%m")
        qtd = sum(1 for item in todos_dados_usuario if item[6] == data_alvo_str)
        
    is_selected = (data_alvo_str == st.session_state.data_selecionada)
    tipo_botao = "primary" if is_selected else "secondary"
    marcador_qtd = f"🟢 {qtd}" if qtd > 0 else f"⚪ {qtd}"
    
    with col:
        if st.button(f"**{label}**  \n{marcador_qtd}", key=f"btn_cron_{data_alvo_str}", type=tipo_botao, use_container_width=True):
            st.session_state.data_selecionada = data_alvo_str
            st.rerun()

with col_next:
    st.write("")
    if st.button("▶️", key="btn_nav_next", use_container_width=True):
        st.session_state.clique_offset += 5
        st.rerun()

if st.session_state.clique_offset != 0 or st.session_state.data_selecionada != hoje_str:
    col_reset, _ = st.columns([2, 5])
    if col_reset.button("🏠 Voltar para o Dia de Hoje", use_container_width=True):
        st.session_state.clique_offset = 0
        st.session_state.data_selecionada = hoje_str
        st.rerun()

st.write("")
st.divider()

# -----------------------------------------------------------------------------
# COMPONENTIZAÇÃO DE ABAS
# -----------------------------------------------------------------------------
tab_fila, tab_cadastro, tab_banco = st.tabs(["Fila Dinâmica", "Inserir Questão", "Banco de Dados"])

# --- TAB 1: FILA DINÂMICA ---
with tab_fila:
    data_sel_obj = datetime.datetime.strptime(st.session_state.data_selecionada, "%d/%m/%Y").date()
    
    fila_filtrada = []
    if st.session_state.data_selecionada == hoje_str:
        fila_filtrada = [item for item in todos_dados_usuario if datetime.datetime.strptime(item[6], "%d/%m/%Y").date() <= hoje_base]
        st.subheader(f"📅 Fila de Hoje (Inclui Atrasadas) — `{len(fila_filtrada)}` pendentes")
    else:
        fila_filtrada = [item for item in todos_dados_usuario if item[6] == st.session_state.data_selecionada]
        st.subheader(f"📅 Agendadas para {st.session_state.data_selecionada} — `{len(fila_filtrada)}` itens")
        
    if not fila_filtrada:
        st.success("🎉 Parabéns, tudo certo por hoje.")
    else:
        for item in fila_filtrada:
            id_q, total_tentativas, sequencia_retencao, ef, inter, ult_dif, prox = item
            with st.container(border=True):
                st.markdown(f"**ID:** `{id_q}`")
                st.caption(f"📊 **Métricas:** Tentativas: `{total_tentativas}` | Retenção Atual: `{sequencia_retencao}` | Fator (EF): `{ef}` | Intervalo atual: `{inter} dias`")
                st.write("**Avalie a dificuldade desta resposta:**")
                
                col0, col1, col2 = st.columns(3)
                col3, col4, col5 = st.columns(3)
                cols_botoes = [col0, col1, col2, col3, col4, col5]
                
                for dif_valor in sorted(ESCALA_DIFICULDADE.keys()):
                    label_btn = ESCALA_DIFICULDADE[dif_valor]
                    if cols_botoes[dif_valor].button(label_btn, key=f"ans_{id_q}_{dif_valor}", use_container_width=True):
                        registrar_resposta_sm2(id_q, dif_valor, questao_existente=(total_tentativas, sequencia_retencao, ef, inter))
                        st.rerun()

# --- TAB 2: INSERIR QUESTÃO ---
with tab_cadastro:
    st.subheader("Registrar entrada de ID")
    id_input = st.text_input("Cole ou digite o ID da questão aqui:").strip()
    
    if id_input:
        registro = next((item for item in todos_dados_usuario if item[0] == id_input), None)
        
        if registro:
            tentativas = registro[1]
            prox_str = registro[6]
            prox_obj = datetime.datetime.strptime(prox_str, "%d/%m/%Y").date()
            
            if prox_obj > hoje_base:
                st.warning(f"A questão `{id_input}` já está programada para revisão futura em: **{prox_str}** (Tentativas até agora: {tentativas}).")
            else:
                st.info(f"A questão `{id_input}` está na fila de hoje. Responda diretamente na aba 'Fila Dinâmica'.")
        else:
            st.write(f"A questão **{id_input}** é inédita na sua conta. Qual foi o seu nível de dificuldade ao tentar respondê-la?")
            
            c0, c1, c2 = st.columns(3)
            c3, c4, c5 = st.columns(3)
            colunas_cadastro = [c0, c1, c2, c3, c4, c5]
            
            for dif_valor in sorted(ESCALA_DIFICULDADE.keys()):
                label_btn = ESCALA_DIFICULDADE[dif_valor]
                if colunas_cadastro[dif_valor].button(label_btn, key=f"cad_ans_{dif_valor}", use_container_width=True):
                    registrar_resposta_sm2(id_input, dif_valor)
                    st.success(f"Questão {id_input} processada e agendada conforme a lógica SM-2!")
                    st.rerun()

# --- TAB 3: BANCO DE DADOS ---
with tab_banco:
    if todos_dados_usuario:
        st.subheader("✏️ Alterar Data de Revisão Manualmente")
        
        dados_ordenados = sorted(todos_dados_usuario, key=lambda x: datetime.datetime.strptime(x[6], "%d/%m/%Y").date())
        
        lista_ids = [item[0] for item in dados_ordenados]
        id_para_editar = st.selectbox("Selecione o ID da questão para modificar:", lista_ids, key="sb_id_editar")
        
        dados_da_questao = next(item for item in dados_ordenados if item[0] == id_para_editar)
        data_atual_str = dados_da_questao[6]
        data_atual_obj = datetime.datetime.strptime(data_atual_str, "%d/%m/%Y").date()
        
        nova_data_input = st.date_input("Selecione a nova data de revisão:", value=data_atual_obj, format="DD/MM/YYYY", key="date_id_editar")
        
        if st.button("Salvar Alteração de Data", use_container_width=True):
            if nova_data_input == data_atual_obj:
                st.info("A data selecionada é igual à data atual da questão.")
            else:
                confirmar_alteracao_dialog(id_para_editar, data_atual_str, nova_data_input)
        
        st.divider()
        
        st.subheader("Suas Questões Salvas (Análise SM-2)")
        df = pd.DataFrame(dados_ordenados, columns=[
            "ID da Questão", "Total de Tentativas", "Sequência de Retenção", "Coeficiente (EF)", "Intervalo (Dias)", "Última Dificuldade", "Próxima Revisão"
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    else:
        st.subheader("Suas Questões Salvas")
        st.info("Você ainda não possui questões registradas nesta conta.")