import streamlit as st
import sqlite3
import datetime
import pandas as pd
import hashlib
import math
import io
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Repeat It", layout="centered")

# -----------------------------------------------------------------------------
# ESTADO DA SESSÃO
# -----------------------------------------------------------------------------
if "usuario" not in st.session_state:
    st.session_state.usuario = None  
if "clique_offset" not in st.session_state:
    st.session_state.clique_offset = 0  
if "data_selecionada" not in st.session_state:
    st.session_state.data_selecionada = datetime.date.today().strftime("%d/%m/%Y")
if "toast_msg" not in st.session_state:
    st.session_state.toast_msg = None

# -----------------------------------------------------------------------------
# BANCO DE DADOS (SQLite)
# -----------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect("repeat_it.db", timeout=10)
    cursor = conn.cursor()
    
    # 1. Primeiro: Cria todas as tabelas garantidamente
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT);
        
        CREATE TABLE IF NOT EXISTS materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            usuario TEXT, 
            nome TEXT, 
            UNIQUE(usuario, nome)
        );
        
        CREATE TABLE IF NOT EXISTS topicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            materia_id INTEGER, 
            usuario TEXT, 
            nome TEXT, 
            FOREIGN KEY(materia_id) REFERENCES materias(id),
            UNIQUE(usuario, materia_id, nome)
        );
        
        CREATE TABLE IF NOT EXISTS questoes_sm2 (
            id_questao TEXT, usuario TEXT, total_tentativas INTEGER,
            sequencia_retencao INTEGER, fator_facilidade REAL, intervalo INTEGER,
            ultimo_dominio INTEGER, proxima_revisao TEXT, materia_id INTEGER,
            topico_id INTEGER, PRIMARY KEY (id_questao, usuario)
        );
        
        CREATE TABLE IF NOT EXISTS questoes_ineditas (
            id_questao TEXT, usuario TEXT, materia_id INTEGER, topico_id INTEGER,
            respondida INTEGER DEFAULT 0, PRIMARY KEY (id_questao, usuario)
        );
    """)
    conn.commit() # Garante que as tabelas existem agora

    # 2. Agora, com segurança, verifica se está vazio
    cursor.execute("SELECT count(*) FROM materias")
    count = cursor.fetchone()[0]

    # 3. Se estiver vazio, popula (AQUI VOCÊ CHAMA A LÓGICA DE POPULAÇÃO)
    if count == 0:
        # Se você tiver os dados aqui no app.py, pode colar a lógica de população aqui
        # Ou simplesmente deixar passar se for popular via script separado depois
        pass 
        
    conn.close()

def popular_edital_automatico(cursor):
    # Insira aqui o dicionário 'edital_data' que criamos

    edital = {
    # Módulo I
    "Língua Portuguesa": [
        "Compreensão e interpretação de textos", "Reconhecimento de tipos e gêneros textuais",
        "Domínio da ortografia oficial", "Domínio dos mecanismos de coesão textual",
        "Emprego de tempos e modos verbais", "Domínio da estrutura morfossintática",
        "Emprego das classes de palavras", "Relações de coordenação e subordinação",
        "Sinais de pontuação", "Concordância verbal e nominal", "Regência verbal e nominal",
        "Crase", "Colocação pronominal", "Reescrita de frases e parágrafos"
    ],
    "Língua Inglesa": [
        "Compreensão de textos e itens gramaticais relevantes"
    ],
    "Raciocínio Lógico": [
        "Estruturas lógicas", "Lógica de argumentação (analogias/inferências)",
        "Lógica sentencial (tabelas-verdade, equivalências)", "Diagramas lógicos",
        "Lógica de primeira ordem", "Problemas aritméticos, geométricos e matriciais"
    ],
    "Atualidades e IA": [
        "Tópicos relevantes e atuais", "Fundamentos de IA (Aprendizado de máquina, Modelos generativos, Governança/Ética)"
    ],
    "Legislação (Segurança e Dados)": [
        "Lei nº 12.527/2011 (LAI)", "Lei nº 12.737/2012 (Delitos Informáticos)",
        "Lei nº 12.965/2014 (Marco Civil da Internet)", "Lei nº 13.709/2018 (LGPD)"
    ],
    # Módulo II
    "Análise de Negócios de TI": [
        "Análise de negócios", "Gestão por processos e funcional (Ciclo PDCA)",
        "Gerenciamento de Processos (BPM CBOK v.4.0)", "Notação BPMN",
        "Ferramentas de gestão (BPMS)", "Gerenciamento de indicadores, metas e resultados",
        "Gestão Ágil de Projetos", "Gerenciamento de produtos", "COBIT 2019", "ITIL v4",
        "Engenharia de software (Estruturado/OO)", "Desenho de Arquitetura de Soluções",
        "User experience (UX: Acessibilidade/Usabilidade/Histórias)", "Storytelling com dados",
        "Prototipação", "Design thinking", "Análise de personas", "Mínimo Produto Viável (MVP)",
        "Técnicas de modelagem e DataMining", "Arquitetura de Dados (Modelagem, SQL, DDL, DML)",
        "Análise de dados e BI (Conceitos, OLAP, Data Warehouse, Dashboards)",
        "Negociação (Conceitos, Conflito, Estilos)", "Comunicação assertiva",
        "Gestão Comercial e Relacionamento com cliente",
        "Gestão de Contratos com Clientes (Formalização/Execução/Precificação)",
        "Conceitos de Inteligência Artificial e Big Data"
    ]
}
    for materia, topicos in edital.items():
        cursor.execute("INSERT INTO materias (usuario, nome) VALUES (?, ?)", ("cassandra", materia))
        mat_id = cursor.lastrowid
        for t in topicos:
            cursor.execute("INSERT INTO topicos (materia_id, usuario, nome) VALUES (?, ?, ?)", (mat_id, "pedro", t))

def migrar_questoes_antigas(cursor):
    try:
        df = pd.read_csv('2026-07-16T12-10_export.csv')
        for _, row in df.iterrows():
            cursor.execute("""INSERT OR REPLACE INTO questoes_sm2 ...""", (...))
    except FileNotFoundError:
        print("Arquivo CSV não encontrado, pulando migração.")


def query_db(query, params=(), fetchall=True):
    with sqlite3.connect("repeat_it.db", timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if query.strip().upper().startswith("SELECT"):
            res = cursor.fetchall() if fetchall else cursor.fetchone()
            return res
        else:
            conn.commit()
            return None

init_db()

def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# -----------------------------------------------------------------------------
# TELA DE AUTENTICAÇÃO
# -----------------------------------------------------------------------------
if st.session_state.usuario is None:
    st.title("Repeat It 🧠")
    st.caption("Estudo ativo e revisão espaçada.")
    st.write("") 
    
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
        with st.form("form_cadastro"):
            user_cad = st.text_input("Escolha um nome de usuário único:", key="cad_user").strip().lower()
            senha_cad = st.text_input("Escolha uma senha forte:", type="password", key="cad_pass")
            senha_cad_conf = st.text_input("Confirme sua senha:", type="password", key="cad_pass_conf")
            botao_cadastro = st.form_submit_button("Criar Conta", use_container_width=True)
            
            if botao_cadastro:
                if user_cad and senha_cad and senha_cad_conf:
                    usuario_existe = query_db("SELECT 1 FROM usuarios WHERE usuario = ?", (user_cad,), fetchall=False)
                    if usuario_existe:
                        st.error(f"❌ O usuário `{user_cad}` já está em uso.")
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
# LÓGICA SM-2 E FILAS
# -----------------------------------------------------------------------------
def calcular_sm2(nivel_dominio, sequencia_retencao, fator_facilidade, intervalo):
    q = nivel_dominio 
    
    if q >= 3:
        if sequencia_retencao == 0: novo_intervalo = 1
        elif sequencia_retencao == 1: novo_intervalo = 6
        else: novo_intervalo = math.ceil(intervalo * fator_facilidade)
        nova_sequencia = sequencia_retencao + 1
    else:
        nova_sequencia = 0
        novo_intervalo = 1
    
    novo_fator = fator_facilidade + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    novo_fator = max(1.3, novo_fator)
    return nova_sequencia, round(novo_fator, 2), novo_intervalo

def registrar_resposta_sm2(id_questao, nivel_dominio, questao_existente=None, materia_id=None, topico_id=None):
    hoje = datetime.date.today()
    if not questao_existente:
        total_tentativas, sequencia_retencao, fator_facilidade, intervalo = 0, 0, 2.5, 0
    else:
        total_tentativas, sequencia_retencao, fator_facilidade, intervalo = questao_existente
        res_chaves = query_db("SELECT materia_id, topico_id FROM questoes_sm2 WHERE id_questao=? AND usuario=?", 
                              (id_questao, st.session_state.usuario), fetchall=False)
        if res_chaves:
            materia_id = res_chaves[0] if materia_id is None else materia_id
            topico_id = res_chaves[1] if topico_id is None else topico_id
        
    nova_sequencia, novo_fator, novo_intervalo = calcular_sm2(nivel_dominio, sequencia_retencao, fator_facilidade, intervalo)
    novo_total = total_tentativas + 1
    proxima_data = hoje + datetime.timedelta(days=novo_intervalo)
    
    query_db(
        """INSERT OR REPLACE INTO questoes_sm2 
           (id_questao, usuario, total_tentativas, sequencia_retencao, fator_facilidade, intervalo, ultimo_dominio, proxima_revisao, materia_id, topico_id) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (id_questao, st.session_state.usuario, novo_total, nova_sequencia, novo_fator, novo_intervalo, nivel_dominio, proxima_data.strftime("%d/%m/%Y"), materia_id, topico_id)
    )

def garantir_materia_topico(nome_materia, nome_topico):
    nome_materia = str(nome_materia).strip()
    nome_topico = str(nome_topico).strip()
    
    try:
        query_db("INSERT INTO materias (usuario, nome) VALUES (?, ?)", (st.session_state.usuario, nome_materia))
    except sqlite3.IntegrityError:
        pass
    mat_id = query_db("SELECT id FROM materias WHERE usuario = ? AND nome = ?", (st.session_state.usuario, nome_materia), fetchall=False)[0]
    
    try:
        query_db("INSERT INTO topicos (materia_id, usuario, nome) VALUES (?, ?, ?)", (mat_id, st.session_state.usuario, nome_topico))
    except sqlite3.IntegrityError:
        pass
    top_id = query_db("SELECT id FROM topicos WHERE materia_id = ? AND usuario = ? AND nome = ?", (mat_id, st.session_state.usuario, nome_topico), fetchall=False)[0]
    
    return mat_id, top_id

# -----------------------------------------------------------------------------
# ESCALA DIAGNÓSTICA (NÍVEL DE DOMÍNIO: 0 A 5)
# -----------------------------------------------------------------------------
ESCALA_DOMINIO = {
    0: "0️⃣ Assunto Inédito / Branco",
    1: "1️⃣ Conhecimento Raso / Chute",
    2: "2️⃣ Exceção / Pegadinha",
    3: "3️⃣ Dúvida entre Duas",
    4: "4️⃣ Hesitação Leve",
    5: "5️⃣ Domínio Total"
}

def gerar_prompt(nivel, acertou):
    if nivel == 4:
        if acertou:
            return "O gabarito desta questão é a alternativa [CORRETA], e eu acertei. Porém, o texto da alternativa [LETRA DA SUA DÚVIDA] me fez hesitar por um momento. Explique em, no máximo, duas linhas qual é a diferença técnica pontual entre elas para eu não hesitar novamente."
        else:
            return "Errei a questão. Marquei a alternativa [SUA RESPOSTA], mas o gabarito é [CORRETA]. Eu hesitei e acabei caindo no erro. Explique em, no máximo, duas linhas qual é o detalhe técnico que invalida a minha resposta e valida o gabarito."
    elif nivel == 3:
        if acertou:
            return "Acertei a questão (gabarito [CORRETA]), mas fiquei em dúvida entre ela e a [LETRA DA SUA DÚVIDA]. Crie uma regra prática direta ou um mnemônico curto para eu diferenciar o conceito das duas com segurança no futuro."
        else:
            return "Errei a questão. Fiquei dividido entre a [SUA RESPOSTA] e o gabarito [CORRETA], e acabei marcando a errada. Crie uma regra prática direta ou mnemônico para eu parar de confundir o conceito da minha resposta com a correta."
    elif nivel == 2:
        if acertou:
            return "Acertei a questão (gabarito [CORRETA]), mas notei que a banca usou uma pegadinha forte ou cobrou uma exceção. Aponte em bullet points curtos qual foi a armadilha semântica ou exceção específica dessa questão, apenas para validar e fixar meu raciocínio."
        else:
            return "Errei essa questão caindo em uma pegadinha ou exceção. Marquei [SUA RESPOSTA] e o gabarito é [CORRETA]. Eu já conheço a regra geral do assunto. Aponte em bullet points curtos exatamente onde está a 'pegadinha' semântica ou qual é a regra de exceção cobrada. Não explique a teoria básica."
    elif nivel == 1:
        if acertou:
            return "Acertei essa questão (gabarito [CORRETA]) puramente no chute ou por intuição rasa. Aplicando o Princípio de Pareto, resuma em 3 tópicos curtos estritamente a regra que eu preciso saber para acertar esse padrão de cobrança sem depender da sorte na próxima vez. Ignore teorias aprofundadas."
        else:
            return "Errei essa questão marcando [SUA RESPOSTA], pois não tenho domínio firme do termo cobrado (chutei). O gabarito é [CORRETA]. Aplicando o Princípio de Pareto, resuma em 3 tópicos curtos e diretos a regra exata que me faria acertar esse formato de questão. Ignore a teoria adjacente."
    elif nivel == 0:
        if acertou:
            return "Acertei essa questão (gabarito [CORRETA]) num chute completamente cego. Não faço ideia do que se trata o assunto principal. Use uma analogia simples para explicar a ideia central do tema e justifique, de forma bem resumida, apenas o porquê do gabarito estar certo."
        else:
            return "Errei essa questão e não tenho nenhum conhecimento prévio sobre o assunto cobrado. O gabarito é [CORRETA]. Use uma analogia simples do dia a dia para me explicar a ideia central do tema e justifique apenas por que a alternativa correta é essa. Não gaste tempo analisando as incorretas."
    return ""

@st.dialog("Confirmar Alteração de Data")
def confirmar_alteracao_dialog(id_q, data_antiga, data_nova):
    st.warning(f"⚠️ Você está prestes a mudar o cronograma da questão: **{id_q}**")
    st.markdown(f"**Data Antiga:** `{data_antiga}`")
    st.markdown(f"**Nova Data:** `{data_nova.strftime('%d/%m/%Y')}`")
    
    col_sim, col_nao = st.columns(2)
    if col_sim.button("Sim, tenho certeza", use_container_width=True, type="primary"):
        query_db(
            "UPDATE questoes_sm2 SET proxima_revisao = ? WHERE id_questao = ? AND usuario = ?", 
            (data_nova.strftime("%d/%m/%Y"), id_q, st.session_state.usuario)
        )
        st.rerun()
    if col_nao.button("Cancelar", use_container_width=True):
        st.rerun()

# -----------------------------------------------------------------------------
# INTERFACE PRINCIPAL
# -----------------------------------------------------------------------------
if st.session_state.toast_msg:
    st.toast(st.session_state.toast_msg[0], icon=st.session_state.toast_msg[1])
    st.session_state.toast_msg = None

col_titulo, col_logout = st.columns([4, 1])
with col_titulo:
    st.title("Repeat It 🧠")
    st.caption(f"Estudo ativo e revisão espaçada. &nbsp; • &nbsp; Conta ativa: **{st.session_state.usuario}**")
with col_logout:
    st.write("") 
    if st.button("Sair ↩️", use_container_width=True):
        st.session_state.usuario = None
        st.rerun()

hoje_base = datetime.date.today()
hoje_str = hoje_base.strftime("%d/%m/%Y")

todos_dados_usuario = query_db("""
    SELECT q.id_questao, q.total_tentativas, q.sequencia_retencao, q.fator_facilidade, 
           q.intervalo, q.ultimo_dominio, q.proxima_revisao,
           IFNULL(m.nome, 'Não Atribuída') as materia_nome, 
           IFNULL(t.nome, 'Não Atribuído') as topico_nome
    FROM questoes_sm2 q
    LEFT JOIN materias m ON q.materia_id = m.id
    LEFT JOIN topicos t ON q.topico_id = t.id
    WHERE q.usuario = ?
""", (st.session_state.usuario,))

# -----------------------------------------------------------------------------
# COMPONENTIZAÇÃO DE ABAS
# -----------------------------------------------------------------------------
tab_fila_sm2, tab_fila_ineditas, tab_cadastro, tab_materias, tab_dash, tab_banco, tab_sobre = st.tabs([
    "Fila Revisão", "Fila Inéditas", "Inserir Única", "Catálogo", "Dashboards", "Banco de Dados", "Sobre"
])

# --- TAB 1: FILA SM-2 (REVISÃO) ---
with tab_fila_sm2:
    st.subheader("📅 Calendário de Revisão")
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
    
    data_sel_obj = datetime.datetime.strptime(st.session_state.data_selecionada, "%d/%m/%Y").date()
    
    fila_filtrada = []
    if st.session_state.data_selecionada == hoje_str:
        fila_filtrada = [item for item in todos_dados_usuario if datetime.datetime.strptime(item[6], "%d/%m/%Y").date() <= hoje_base]
        st.write(f"**Fila de Hoje** — `{len(fila_filtrada)}` pendentes")
    else:
        fila_filtrada = [item for item in todos_dados_usuario if item[6] == st.session_state.data_selecionada]
        st.write(f"**Agendadas para {st.session_state.data_selecionada}** — `{len(fila_filtrada)}` itens")
        
    if not fila_filtrada:
        st.success("🎉 Parabéns, fila de revisão zerada. Vá para a Fila de Inéditas!")
    else:
        for item in fila_filtrada:
            id_q, total_tentativas, sequencia_retencao, ef, inter, ult_dif, prox, mat_nome, top_nome = item
            with st.container(border=True):
                st.markdown(f"**ID:** `{id_q}`")
                st.markdown(f"📚 **Matéria:** `{mat_nome}` | 📌 **Tópico:** `{top_nome}`")
                st.caption(f"📊 **Métricas:** Tentativas: `{total_tentativas}` | Retenção Atual: `{sequencia_retencao}` | Fator (EF): `{ef}` | Intervalo atual: `{inter} dias`")
                st.write("**Nível de Domínio no resgate da memória:**")
                
                col0, col1, col2 = st.columns(3)
                col3, col4, col5 = st.columns(3)
                cols_botoes = [col0, col1, col2, col3, col4, col5]
                
                for dif_valor in sorted(ESCALA_DOMINIO.keys()):
                    label_btn = ESCALA_DOMINIO[dif_valor]
                    if cols_botoes[dif_valor].button(label_btn, key=f"ans_{id_q}_{dif_valor}", use_container_width=True):
                        registrar_resposta_sm2(id_q, dif_valor, questao_existente=(total_tentativas, sequencia_retencao, ef, inter))
                        st.rerun()

# --- TAB 2: FILA DE INÉDITAS ---
with tab_fila_ineditas:
    st.subheader("Questões Inéditas (Estudo Reverso)")
    
    questoes_virgens = query_db("""
        SELECT q.id_questao, m.nome, t.nome, q.materia_id, q.topico_id 
        FROM questoes_ineditas q
        JOIN materias m ON q.materia_id = m.id
        JOIN topicos t ON q.topico_id = t.id
        WHERE q.usuario = ? AND q.respondida = 0
    """, (st.session_state.usuario,))
    
    with st.expander("📥 Importar Planilha de Questões"):
        st.write("Baixe o modelo, preencha as questões e faça o upload para gerar sua fila.")
        
        df_modelo = pd.DataFrame(columns=["ID_Questao", "Materia", "Topico"])
        csv_buffer = io.BytesIO()
        df_modelo.to_csv(csv_buffer, index=False)
        st.download_button(label="Baixar Planilha Modelo", data=csv_buffer.getvalue(), file_name="modelo_questoes.csv", mime="text/csv")
        
        arquivo_upload = st.file_uploader("Faça upload do CSV preenchido", type=["csv"])
        if arquivo_upload is not None:
            if st.button("Processar Lote", type="primary"):
                try:
                    df_upload = pd.read_csv(arquivo_upload)
                    novas = 0
                    for index, row in df_upload.iterrows():
                        id_q = str(row['ID_Questao']).strip()
                        mat = str(row['Materia']).strip()
                        top = str(row['Topico']).strip()
                        
                        mat_id, top_id = garantir_materia_topico(mat, top)
                        try:
                            query_db("INSERT INTO questoes_ineditas (id_questao, usuario, materia_id, topico_id) VALUES (?, ?, ?, ?)", 
                                     (id_q, st.session_state.usuario, mat_id, top_id))
                            novas += 1
                        except sqlite3.IntegrityError:
                            pass
                    st.session_state.toast_msg = (f"{novas} questões processadas e adicionadas à fila de inéditas.", "✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao processar arquivo. Verifique se o formato está correto. Detalhe: {e}")
                    
    st.divider()
    
    if not questoes_virgens:
        st.info("Sua fila de inéditas está vazia. Importe questões via planilha.")
    else:
        q_atual = questoes_virgens[0]
        id_q, mat_nome, top_nome, mat_id, top_id = q_atual
        
        st.markdown(f"### Restam `{len(questoes_virgens)}` inéditas")
        with st.container(border=True):
            st.markdown(f"**ID:** `{id_q}`")
            st.markdown(f"📚 **Matéria:** `{mat_nome}` | 📌 **Tópico:** `{top_nome}`")
            st.write("---")
            
            resultado = st.radio("1. Qual foi o resultado prático após verificar o gabarito?", 
                                 ["Selecione...", "✅ Acertei", "❌ Errei"], horizontal=True, key=f"rad_res_{id_q}")
            
            opcoes_escala = ["Selecione..."] + [ESCALA_DOMINIO[k] for k in sorted(ESCALA_DOMINIO.keys())]
            sentimento = st.radio("2. Qual o seu nível real de domínio sobre a questão?", 
                                  options=opcoes_escala, horizontal=True, key=f"rad_sen_{id_q}")
            
            if resultado != "Selecione..." and sentimento != "Selecione...":
                nivel = int(sentimento[0])
                acertou_bool = (resultado == "✅ Acertei")
                
                st.write("---")
                if nivel == 5:
                    st.success("Tudo certo! Nenhuma intervenção necessária. Padrão consolidado.")
                else:
                    st.markdown("**3. Ação Ágil:** *Copie o texto abaixo e aplique na IA.*")
                    st.code(gerar_prompt(nivel, acertou_bool), language="markdown", wrap_lines=True)
                
                if st.button("📥 Registrar na Fila de Revisão SM-2", type="primary", use_container_width=True):
                    dificuldade_sm2 = nivel if acertou_bool else 0
                    registrar_resposta_sm2(id_q, dificuldade_sm2, materia_id=mat_id, topico_id=top_id)
                    query_db("UPDATE questoes_ineditas SET respondida = 1 WHERE id_questao = ? AND usuario = ?", (id_q, st.session_state.usuario))
                    st.rerun()

# --- TAB 3: INSERIR QUESTÃO ÚNICA (SM-2 Direto) ---
with tab_cadastro:
    st.subheader("Inserção Direta (Fora da Fila)")
    
    lista_materias = query_db("SELECT id, nome FROM materias WHERE usuario = ?", (st.session_state.usuario,))
    
    if not lista_materias:
        st.warning("⚠️ Cadastre matérias no Catálogo antes de inserir.")
    else:
        col_m, col_t = st.columns(2)
        with col_m:
            mat_opcoes = {m[1]: m[0] for m in lista_materias}
            mat_selecionada = st.selectbox("Selecione a Matéria:", list(mat_opcoes.keys()), key="sel_mat_cad")
            mat_id = mat_opcoes[mat_selecionada]
            
        with col_t:
            lista_topicos = query_db("SELECT id, nome FROM topicos WHERE materia_id = ? AND usuario = ?", (mat_id, st.session_state.usuario))
            if not lista_topicos:
                st.warning("⚠️ Sem tópicos.")
                top_id = None
            else:
                top_opcoes = {t[1]: t[0] for t in lista_topicos}
                top_selecionado = st.selectbox("Selecione o Tópico:", list(top_opcoes.keys()), key="sel_top_cad")
                top_id = top_opcoes[top_selecionado]

        if lista_topicos:
            st.write("")
            id_input = st.text_input("ID da questão (Pressione Enter):").strip()
            
            if id_input:
                registro = next((item for item in todos_dados_usuario if item[0] == id_input), None)
                if registro:
                    st.warning("Questão já no banco SM-2.")
                else:
                    st.write("Avalie seu Nível de Domínio inicial:")
                    c0, c1, c2 = st.columns(3)
                    c3, c4, c5 = st.columns(3)
                    colunas_cadastro = [c0, c1, c2, c3, c4, c5]
                    
                    for dif_valor in sorted(ESCALA_DOMINIO.keys()):
                        if colunas_cadastro[dif_valor].button(ESCALA_DOMINIO[dif_valor], key=f"cad_ans_{dif_valor}", use_container_width=True):
                            registrar_resposta_sm2(id_input, dif_valor, materia_id=mat_id, topico_id=top_id)
                            st.success(f"Questão agendada!")
                            st.rerun()

# --- TAB 4: CATÁLOGO ---
with tab_materias:
    st.subheader("Configurar Organização do Catálogo")
    with st.container(border=True):
        st.write("**Adicionar Matéria ou Tópico**")
        
        lista_materias_form = query_db("SELECT id, nome FROM materias WHERE usuario = ? ORDER BY nome", (st.session_state.usuario,))
        opcoes_mat = ["+ Criar Nova Matéria..."] + [m[1] for m in lista_materias_form]
        
        materia_selecionada = st.selectbox("Selecione a Matéria ou crie uma nova:", opcoes_mat, key="sel_mat_unica")
        
        with st.form("form_mat_top", clear_on_submit=True, border=False):
            if materia_selecionada == "+ Criar Nova Matéria...":
                nome_mat_input = st.text_input("Nome da Nova Matéria:")
            else:
                nome_mat_input = materia_selecionada
                
            nome_top_input = st.text_input("Nome do Tópico (deixe em branco para salvar apenas a matéria):")
            
            if st.form_submit_button("Salvar Matéria/Tópico", use_container_width=True, type="primary"):
                nome_mat_final = nome_mat_input.strip() if materia_selecionada == "+ Criar Nova Matéria..." else materia_selecionada
                nome_top_final = nome_top_input.strip()
                
                if materia_selecionada == "+ Criar Nova Matéria..." and not nome_mat_final:
                    st.session_state.toast_msg = ("Defina o nome da matéria antes de salvar.", "⚠️")
                    st.rerun()
                    
                mat_id = None
                mat_nova_salva = False
                
                if materia_selecionada == "+ Criar Nova Matéria...":
                    try:
                        query_db("INSERT INTO materias (usuario, nome) VALUES (?, ?)", (st.session_state.usuario, nome_mat_final))
                        mat_nova_salva = True
                    except sqlite3.IntegrityError:
                        pass 
                        
                res = query_db("SELECT id FROM materias WHERE usuario = ? AND nome = ?", (st.session_state.usuario, nome_mat_final), fetchall=False)
                
                if res:
                    mat_id = res[0]
                    if nome_top_final:
                        try:
                            query_db("INSERT INTO topicos (materia_id, usuario, nome) VALUES (?, ?, ?)", 
                                     (mat_id, st.session_state.usuario, nome_top_final))
                            st.session_state.toast_msg = (f"Tópico '{nome_top_final}' salvo na matéria '{nome_mat_final}'!", "✅")
                        except sqlite3.IntegrityError:
                            st.session_state.toast_msg = (f"O tópico '{nome_top_final}' já existe em '{nome_mat_final}'.", "❌")
                    else:
                        if mat_nova_salva:
                            st.session_state.toast_msg = (f"Matéria '{nome_mat_final}' salva com sucesso!", "✅")
                        else:
                            st.session_state.toast_msg = ("Essa matéria já estava cadastrada e nenhum tópico foi inserido.", "ℹ️")
                else:
                    st.session_state.toast_msg = ("Erro ao localizar ou criar a matéria.", "❌")
                st.rerun()

    st.divider()
    
    st.subheader("📚 Seu Catálogo Atual")
    
    materias_cadastradas = query_db("SELECT id, nome FROM materias WHERE usuario = ? ORDER BY nome", (st.session_state.usuario,))
    
    if not materias_cadastradas:
        st.info("Você ainda não tem matérias cadastradas no seu catálogo.")
    else:
        for mat_id, mat_nome in materias_cadastradas:
            with st.expander(f"📖 **{mat_nome}**"):
                topicos_cadastrados = query_db("SELECT id, nome FROM topicos WHERE materia_id = ? AND usuario = ? ORDER BY nome", (mat_id, st.session_state.usuario))
                
                if not topicos_cadastrados:
                    st.write("*Nenhum tópico cadastrado nesta matéria.*")
                else:
                    for top_id, top_nome in topicos_cadastrados:
                        st.markdown(f"- {top_nome}")

# --- TAB 5: DASHBOARDS ---
with tab_dash:
    if not todos_dados_usuario:
        st.info("💡 Não há dados suficientes. Realize algumas questões e revisões para gerar os dashboards.")
    else:
        # Preparando os dados em Pandas
        df_dash = pd.DataFrame(todos_dados_usuario, columns=[
            "id_questao", "total_tentativas", "sequencia_retencao", "fator_facilidade", 
            "intervalo", "ultimo_dominio", "proxima_revisao", "materia_nome", "topico_nome"
        ])
        
        # 1. Previsão de Carga (Forecast de Revisão)
        st.subheader("Previsão de Carga (Próximos 14 dias)")
        df_dash['proxima_revisao_dt'] = pd.to_datetime(df_dash['proxima_revisao'], format='%d/%m/%Y')
        hoje_dt = pd.to_datetime(hoje_str, format='%d/%m/%Y')
        df_forecast = df_dash[df_dash['proxima_revisao_dt'] >= hoje_dt].groupby('proxima_revisao_dt').size().reset_index(name='Quantidade')
        df_forecast = df_forecast.sort_values('proxima_revisao_dt').head(14)
        df_forecast['Data'] = df_forecast['proxima_revisao_dt'].dt.strftime('%d/%m')
        
        if df_forecast.empty:
            st.write("Nenhuma revisão agendada para os próximos dias.")
        else:
            fig1 = px.bar(df_forecast, x='Data', y='Quantidade', text_auto=True, color_discrete_sequence=['#4C78A8'])
            fig1.update_layout(xaxis_title="", yaxis_title="Pendências", margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig1, use_container_width=True)
            
        st.divider()
        
        col_graf1, col_graf2 = st.columns(2)
        
        # 2. O Gráfico de Pareto (Radar de Fraquezas)
        with col_graf1:
            st.subheader("Radar de Fraquezas (Bottom 5)")
            df_pareto = df_dash.groupby('materia_nome')['ultimo_dominio'].mean().reset_index()
            # Pega as 5 piores médias (ordem crescente)
            df_pareto = df_pareto.sort_values('ultimo_dominio').head(5)
            # Para o Plotly exibir de cima pra baixo a menor nota, precisamos ordenar de forma reversa
            df_pareto = df_pareto.sort_values('ultimo_dominio', ascending=False)
            
            fig2 = px.bar(df_pareto, x='ultimo_dominio', y='materia_nome', orientation='h', text_auto='.2f', color_discrete_sequence=['#E45756'])
            fig2.update_layout(xaxis_title="Média de Domínio (0 a 5)", yaxis_title="", margin=dict(l=0, r=0, t=30, b=0))
            fig2.update_xaxes(range=[0, 5])
            st.plotly_chart(fig2, use_container_width=True)

        # 3. Distribuição de Domínio (Saúde Geral)
        with col_graf2:
            st.subheader("Saúde Geral (Por Domínio)")
            df_donut = df_dash.groupby('ultimo_dominio').size().reset_index(name='Quantidade')
            
            # Mapeando os nomes da escala para o gráfico
            mapeamento_nomes = {k: v.split(" ", 1)[1] for k, v in ESCALA_DOMINIO.items()}
            df_donut['Nome_Dominio'] = df_donut['ultimo_dominio'].map(lambda x: f"{x} - {mapeamento_nomes[x]}")
            
            fig3 = px.pie(df_donut, values='Quantidade', names='Nome_Dominio', hole=0.5)
            fig3.update_layout(margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig3, use_container_width=True)

        st.divider()

        # 4. Maturidade da Memória (Funil de Retenção)
        st.subheader("Maturidade da Memória")
        def categorizar_intervalo(dias):
            if dias < 7: return "Curto Prazo (<7 dias)"
            elif dias <= 21: return "Médio Prazo (7-21 dias)"
            else: return "Longo Prazo (>21 dias)"
            
        df_dash['Categoria_Retencao'] = df_dash['intervalo'].apply(categorizar_intervalo)
        df_funnel = df_dash['Categoria_Retencao'].value_counts().reset_index()
        df_funnel.columns = ['Categoria', 'Quantidade']
        
        ordem = ["Curto Prazo (<7 dias)", "Médio Prazo (7-21 dias)", "Longo Prazo (>21 dias)"]
        df_funnel['Categoria'] = pd.Categorical(df_funnel['Categoria'], categories=ordem, ordered=True)
        df_funnel = df_funnel.sort_values('Categoria')
        
        fig4 = px.bar(df_funnel, x='Categoria', y='Quantidade', text_auto=True, color='Categoria',
                      color_discrete_map={"Curto Prazo (<7 dias)": "#F58518", 
                                          "Médio Prazo (7-21 dias)": "#F4CA16", 
                                          "Longo Prazo (>21 dias)": "#54A24B"})
        fig4.update_layout(xaxis_title="", yaxis_title="Qtd. Questões", margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

# --- TAB 6: BANCO DE DADOS ---
with tab_banco:
    if todos_dados_usuario:
        st.subheader("Suas Questões Salvas (Análise SM-2)")
        dados_ordenados = sorted(todos_dados_usuario, key=lambda x: datetime.datetime.strptime(x[6], "%d/%m/%Y").date())
        df = pd.DataFrame(dados_ordenados, columns=[
            "ID da Questão", "Total de Tentativas", "Sequência de Retenção", "Coeficiente (EF)", 
            "Intervalo (Dias)", "Último Domínio", "Próxima Revisão", "Matéria", "Tópico"
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Sem questões registradas.")

# --- TAB 7: SOBRE ---
with tab_sobre:
    st.header("Sobre o Repeat It")
    st.markdown("O **Repeat It** combina duas técnicas poderosas para maximizar a retenção de longo prazo e minimizar o desperdício de tempo: o **Estudo Reverso** guiado pelo Princípio de Pareto e o algoritmo de repetição espaçada **SuperMemo 2 (SM-2)**.")
    
    st.divider()
    
    st.subheader("1. O Princípio do Estudo Reverso")
    st.markdown("""
    A abordagem padrão ensina a estudar toda a teoria antes de tentar resolver questões. O Estudo Reverso inverte isso: você começa pela questão e vai para a teoria apenas para preencher lacunas específicas de conhecimento.
    
    Isso é suportado pelo **Princípio de Pareto (A regra 80/20)**, que sugere que cerca de 20% do material teórico é responsável por resolver 80% das questões das provas. Nosso aplicativo obriga você a identificar exatamente qual é a lacuna (*"Foi uma pegadinha?", "Eu hesitei?", "Não sei o conceito base?"*) e gera prompts dinâmicos para a IA entregar **apenas a regra necessária**, ignorando toda a burocracia do entorno.
    """)
    
    st.divider()
    
    st.subheader("2. O Algoritmo SM-2 (Adaptado)")
    st.markdown("""
    O **SuperMemo 2** é uma fórmula matemática desenhada para prever o momento exato em que seu cérebro está prestes a esquecer uma informação, forçando a revisão na véspera do esquecimento.
    
    No nosso aplicativo, substituímos os botões subjetivos de "Difícil" ou "Fácil" por uma **Escala Diagnóstica de Nível de Domínio (0 a 5)**.
    """)
    
    # Renderização da fórmula oficial baseada em Nível de Domínio
    st.markdown("A matemática do agendamento avalia a qualidade da sua resposta $q$ (que equivale ao seu Nível de Domínio de $0$ a $5$). Se $q \\ge 3$, o resgate da memória foi bem sucedido e a sequência continua:")
    
    st.latex(r"I(1) = 1")
    st.latex(r"I(2) = 6")
    st.latex(r"I(n) = \lceil I(n-1) \times EF \rceil")
    
    st.markdown("Se $q < 3$, a qualidade foi inaceitável. O cérebro falhou em resgatar a informação, a sequência é zerada e a revisão reagendada para o dia seguinte ($I = 1$).")
    
    st.markdown("A cada interação, a dificuldade da questão (Fator de Facilidade - $EF$) é reajustada usando a seguinte fórmula de regressão:")
    
    st.latex(r"EF = EF + (0.1 - (5 - q) \times (0.08 + (5 - q) \times 0.02))")
    
    st.markdown("*(O $EF$ nunca é reduzido para menos de $1.3$ para evitar revisões exaustivas e travamento da fila).*")
    
    st.divider()
    
    st.subheader("A Tática do 'Acerto Ponderado'")
    st.markdown("""
    Ao alimentar questões na **Fila de Inéditas**, o aplicativo usa o "Acerto Ponderado". 
    Isso significa que acertar uma questão porque você teve uma Dúvida Leve gera um comportamento matemático diferente de acertá-la por um Chute Cego.
    Se o seu nível de domínio informado for 0, 1 ou 2, o sistema **sobrepõe o acerto** e diz ao banco de dados que a qualidade foi $0$, forçando a questão a aparecer para revisão já no dia seguinte, blindando o seu longo prazo contra a falsa segurança de um acerto na sorte.
    """)