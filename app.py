import streamlit as st
import sqlite3
import datetime
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Repeat It - Revisão Espaçada", layout="centered")

# -----------------------------------------------------------------------------
# ESTADO DA SESSÃO (Navegação e Filtros)
# -----------------------------------------------------------------------------
if "clique_offset" not in st.session_state:
    st.session_state.clique_offset = 0  
if "data_selecionada" not in st.session_state:
    st.session_state.data_selecionada = datetime.date.today().strftime("%Y-%m-%d")

# -----------------------------------------------------------------------------
# BANCO DE DADOS (SQLite)
# -----------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect("revisoes.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questoes (
            id_questao TEXT PRIMARY KEY,
            nivel_atual INTEGER,
            proxima_revisao TEXT
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

# Inicialização da base de dados local
init_db()

# -----------------------------------------------------------------------------
# LÓGICA DO ALGORITMO DE REVISÃO ESPAÇADA
# -----------------------------------------------------------------------------
def mapear_dias(nivel):
    niveis = {1: 1, 2: 7, 3: 30, 4: 90}
    return niveis.get(nivel, 90)

def salvar_mudanca(id_questao, nivel, dias_para_adicionar):
    hoje = datetime.date.today()
    proxima_data = hoje + datetime.timedelta(days=dias_para_adicionar)
    query_db(
        "INSERT OR REPLACE INTO questoes (id_questao, nivel_atual, proxima_revisao) VALUES (?, ?, ?)",
        (id_questao, nivel, proxima_data.strftime("%Y-%m-%d"))
    )

def registrar_resposta(id_questao, teve_dificuldade, questao_existente=None):
    if not questao_existente:
        if teve_dificuldade:
            salvar_mudanca(id_questao, nivel=1, dias_para_adicionar=1)
        else:
            salvar_mudanca(id_questao, nivel=3, dias_para_adicionar=30)
    else:
        if teve_dificuldade:
            salvar_mudanca(id_questao, nivel=1, dias_para_adicionar=1)
        else:
            nivel_atual = questao_existente[0]
            if nivel_atual == 1: novo_nivel = 2
            elif nivel_atual == 2: novo_nivel = 3
            elif nivel_atual == 3: novo_nivel = 4
            else: novo_nivel = 4
            
            salvar_mudanca(id_questao, nivel=novo_nivel, dias_para_adicionar=mapear_dias(novo_nivel))

# -----------------------------------------------------------------------------
# POPUP DE CONFIRMAÇÃO DIALOG (Modificação Manual)
# -----------------------------------------------------------------------------
@st.dialog("Confirmar Alteração de Data")
def confirmar_alteracao_dialog(id_q, data_antiga, data_nova):
    st.warning(f"⚠️ Você está prestes a mudar o cronograma da questão: **{id_q}**")
    st.markdown(f"**Data Antiga:** `{data_antiga}`")
    st.markdown(f"**Nova Data:** `{data_nova.strftime('%Y-%m-%d')}`")
    st.write("Tem certeza que deseja aplicar essa mudança manual?")
    
    col_sim, col_nao = st.columns(2)
    if col_sim.button("Sim, tenho certeza", use_container_width=True, type="primary"):
        query_db("UPDATE questoes SET proxima_revisao = ? WHERE id_questao = ?", (data_nova.strftime("%Y-%m-%d"), id_q))
        st.rerun()
    if col_nao.button("Cancelar", use_container_width=True):
        st.rerun()

# -----------------------------------------------------------------------------
# INTERFACE PRINCIPAL
# -----------------------------------------------------------------------------
st.title("Repeat It 🧠")
st.caption("Gerenciador Adaptativo de Revisão Espaçada")

hoje_base = datetime.date.today()
hoje_str = hoje_base.strftime("%Y-%m-%d")

# --- BARRA DE CRONOGRAMA NAVEGÁVEL ---
st.write("")
col_prev, *cols_dias, col_next = st.columns([0.6, 1, 1, 1, 1, 1, 0.6])

# Botão Esquerda (Navegar no tempo)
with col_prev:
    st.write("")  
    if st.button("◀️", key="btn_nav_prev", use_container_width=True):
        st.session_state.clique_offset -= 1
        st.rerun()

# Geração dos cards de dias espelhados no offset corrente
for i, col in enumerate(cols_dias):
    data_alvo = hoje_base + datetime.timedelta(days=st.session_state.clique_offset + i)
    data_alvo_str = data_alvo.strftime("%Y-%m-%d")
    
    if data_alvo_str == hoje_str:
        label = "Hoje"
        # O dia corrente contabiliza as pendências atuais + atrasos históricos
        qtd = query_db("SELECT COUNT(*) FROM questoes WHERE proxima_revisao <= ?", (hoje_str,), fetchall=False)[0]
    elif data_alvo_str == (hoje_base + datetime.timedelta(days=1)).strftime("%Y-%m-%d"):
        label = "Amanhã"
        qtd = query_db("SELECT COUNT(*) FROM questoes WHERE proxima_revisao = ?", (data_alvo_str,), fetchall=False)[0]
    else:
        label = data_alvo.strftime("%d/%m")
        qtd = query_db("SELECT COUNT(*) FROM questoes WHERE proxima_revisao = ?", (data_alvo_str,), fetchall=False)[0]
        
    is_selected = (data_alvo_str == st.session_state.data_selecionada)
    tipo_botao = "primary" if is_selected else "secondary"
    marcador_qtd = f"🟢 {qtd}" if qtd > 0 else f"⚪ {qtd}"
    
    with col:
        if st.button(f"**{label}**  \n{marcador_qtd}", key=f"btn_cron_{data_alvo_str}", type=tipo_botao, use_container_width=True):
            st.session_state.data_selecionada = data_alvo_str
            st.rerun()

# Botão Direita (Navegar no tempo)
with col_next:
    st.write("")
    if st.button("▶️", key="btn_nav_next", use_container_width=True):
        st.session_state.clique_offset += 1
        st.rerun()

# Botão de retorno rápido ao marco zero
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
tab_fila, tab_cadastro, tab_banco = st.tabs(["Fila Dinâmica", "Inserir Questão", "Base de Dados"])

# --- TAB 1: FILA DINÂMICA (Escopo Dinâmico) ---
with tab_fila:
    data_sel_obj = datetime.datetime.strptime(st.session_state.data_selecionada, "%Y-%m-%d").date()
    
    if st.session_state.data_selecionada == hoje_str:
        fila_filtrada = query_db(
            "SELECT id_questao, nivel_atual, proxima_revisao FROM questoes WHERE proxima_revisao <= ? ORDER BY id_questao",
            (hoje_str,)
        )
        st.subheader(f"📅 Fila de Hoje (Inclui Atrasadas) — `{len(fila_filtrada)}` pendentes")
    else:
        fila_filtrada = query_db(
            "SELECT id_questao, nivel_atual, proxima_revisao FROM questoes WHERE proxima_revisao = ? ORDER BY id_questao",
            (st.session_state.data_selecionada,)
        )
        st.subheader(f"📅 Agendadas para {data_sel_obj.strftime('%d/%m/%Y')} — `{len(fila_filtrada)}` itens")
        
    if not fila_filtrada:
        st.info("Nenhuma revisão agendada para o dia selecionado.")
    else:
        for item in fila_filtrada:
            id_q, nivel, prox = item
            with st.container():
                col_info, col_btn1, col_btn2 = st.columns([2, 1, 1])
                col_info.markdown(f"**ID:** `{id_q}`  \n*Nível atual: {nivel} (Data alvo: {prox})*")
                
                if col_btn1.button("Tive Dificuldade", key=f"dif_{id_q}", use_container_width=True):
                    registrar_resposta(id_q, teve_dificuldade=True, questao_existente=(nivel, prox))
                    st.rerun()
                    
                if col_btn2.button("Sem Dificuldade", key=f"sem_{id_q}", use_container_width=True):
                    registrar_resposta(id_q, teve_dificuldade=False, questao_existente=(nivel, prox))
                    st.rerun()
            st.divider()

# --- TAB 2: INSERIR QUESTÃO ---
with tab_cadastro:
    st.subheader("Registrar entrada de ID")
    id_input = st.text_input("Cole ou digite o ID da questão aqui:").strip()
    
    if id_input:
        registro = query_db("SELECT nivel_atual, proxima_revisao FROM questoes WHERE id_questao = ?", (id_input,), fetchall=False)
        
        if registro:
            nivel, prox = registro
            if prox > hoje_str:
                st.warning(f"A questão `{id_input}` já está programada para revisão futura em: **{prox}** (Nível {nivel}).")
            else:
                st.info(f"A questão `{id_input}` está na fila de hoje. Responda diretamente na aba 'Fila Dinâmica'.")
        else:
            st.write(f"A questão **{id_input}** é inédita na base de dados. Como foi o seu desempenho nela?")
            col_man1, col_man2 = st.columns(2)
            
            if col_man1.button("Tive Dificuldade", key="btn_man_dif", use_container_width=True):
                registrar_resposta(id_input, teve_dificuldade=True)
                st.success(f"Questão {id_input} agendada para amanhã!")
                st.rerun()
                
            if col_man2.button("Sem Dificuldade", key="btn_man_sem", use_container_width=True):
                registrar_resposta(id_input, teve_dificuldade=False)
                st.success(f"Questão {id_input} agendada para daqui a 1 mês!")
                st.rerun()

# --- TAB 3: BASE DE DADOS ---
with tab_banco:
    todos_dados = query_db("SELECT id_questao, nivel_atual, proxima_revisao FROM questoes ORDER BY proxima_revisao ASC")
    
    if todos_dados:
        st.subheader("✏️ Alterar Data de Revisão Manualmente")
        
        lista_ids = [item[0] for item in todos_dados]
        id_para_editar = st.selectbox("Selecione o ID da questão para modificar:", lista_ids, key="sb_id_editar")
        
        dados_da_questao = next(item for item in todos_dados if item[0] == id_para_editar)
        data_atual_str = dados_da_questao[2]
        data_atual_obj = datetime.datetime.strptime(data_atual_str, "%Y-%m-%d").date()
        
        nova_data_input = st.date_input("Selecione a nova data de revisão:", value=data_atual_obj, key="date_id_editar")
        
        if st.button("Salvar Alteração de Data", use_container_width=True):
            if nova_data_input == data_atual_obj:
                st.info("A data selecionada é igual à data atual da questão.")
            else:
                confirmar_alteracao_dialog(id_para_editar, data_atual_str, nova_data_input)
        
        st.divider()
        
        st.subheader("Todas as Questões Salvas")
        df = pd.DataFrame(todos_dados, columns=["ID da Questão", "Nível Atual", "Próxima Revisão"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    else:
        st.subheader("Todas as Questões Salvas")
        st.info("Nenhuma questão registrada no banco local até o momento.")