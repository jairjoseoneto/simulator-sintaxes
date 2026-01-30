import streamlit as st
import pandas as pd
import numpy as np

# --- CONFIGURAÇÃO INICIAL (SÓBRIA) ---
st.set_page_config(page_title="Sin Tax Simulation", layout="wide")

st.title("Sin Tax Simulation")
st.markdown("Simulação do impacto de políticas fiscais (**Sin Taxes**) na dinâmica populacional e na saúde pública ao longo de 15 anos.")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Intervenção Política")
    tax_hike = st.slider("Aumento de Imposto (%)", 0, 100, 0, help="Aumento percentual sobre a taxa atual.")
    
    st.markdown("---")
    
    st.header("2. Calibragem do Modelo")
    pop_total = st.number_input("População Total (Milhões)", value=200.0)
    prevalence_initial = st.slider("Prevalência Inicial de Fumantes (%)", 5, 50, 15) / 100.0
    
    st.markdown("---")
    
    st.header("3. Parâmetros")
    price_elasticity = st.number_input(
        "Elasticidade-Preço da Demanda", 
        value=-0.40, 
        step=0.05, 
        max_value=0.0,
        format="%.2f",
        help="Sensibilidade da demanda ao preço (Valor negativo usual)."
    )
    
    st.markdown("### Custos de Saúde (Estimativa)")
    cost_per_smoker = st.number_input("Custo Anual por Fumante (R$)", value=3500.0, step=100.0)
    cost_per_ex_smoker = st.number_input("Custo Anual por Ex-Fumante (R$)", value=1500.0, step=100.0)

# --- MOTOR DO MODELO AJUSTADO ---
def run_simulation(years=15): 
    history = []
    
    # Estado Inicial (t=0)
    S_t = pop_total * prevalence_initial
    N_t = pop_total * (1 - prevalence_initial) 
    E_t = 0.0
    
    # --- AJUSTE DE CALIBRAGEM (NATURAL RATES) ---
    # Reduzi levemente a iniciação para o gráfico não subir sozinho se a prevalência for baixa
    rate_initiation = 0.010 # Era 0.015
    rate_cessation  = 0.040
    rate_relapse    = 0.010
    
    # 1. REGISTRA O ANO BASE (2025) ANTES DO CHOQUE
    # Isso garante que o gráfico comece no valor que você escolheu (ex: 13%)
    history.append({
        "Ano": "2025",
        "Prevalência (%)": (S_t / pop_total) * 100,
        "Fumantes (M)": S_t,
        "Ex-Fumantes (M)": E_t,
        "Custo Saúde (Bilhões R$)": (S_t * cost_per_smoker * 1_000_000) / 1_000_000_000
    })
    
    # Intervenção (Cálculo do Choque)
    tax_decimal = tax_hike / 100.0
    
    # Choque Imediato
    immediate_shock_factor = 0.0
    if tax_decimal > 0:
        immediate_shock_factor = tax_decimal * price_elasticity
    
    shock_quitters = S_t * abs(immediate_shock_factor)
    S_t -= shock_quitters
    E_t += shock_quitters

    # Mudança nas Taxas (Longo Prazo)
    impact_initiation = 1 + (tax_decimal * price_elasticity)
    impact_cessation = 1 - (tax_decimal * price_elasticity * 1.5)
    impact_relapse = 1 + (tax_decimal * price_elasticity)

    adj_initiation = rate_initiation * max(0, impact_initiation)
    adj_cessation  = rate_cessation  * impact_cessation
    adj_relapse    = rate_relapse    * max(0, impact_relapse)

    # Loop Temporal (Começa em 2026, pós-choque)
    start_year = 2026
    for year in range(start_year, start_year + years):
        
        new_smokers = N_t * adj_initiation
        quitters    = S_t * adj_cessation
        relapsers   = E_t * adj_relapse
        
        N_next = N_t - new_smokers
        S_next = S_t + new_smokers - quitters + relapsers
        E_next = E_t + quitters - relapsers
        
        N_t, S_t, E_t = N_next, S_next, E_next
        
        annual_cost = (S_t * cost_per_smoker * 1_000_000) + (E_t * cost_per_ex_smoker * 1_000_000)
        current_prevalence = (S_t / pop_total) * 100
        
        history.append({
            "Ano": str(year),
            "Prevalência (%)": current_prevalence,
            "Fumantes (M)": S_t,
            "Ex-Fumantes (M)": E_t,
            "Custo Saúde (Bilhões R$)": annual_cost / 1_000_000_000
        })
        
    return pd.DataFrame(history), adj_initiation, adj_cessation, adj_relapse

# --- EXECUÇÃO ---
df_results, final_init, final_cess, final_rel = run_simulation()

# --- VISUALIZAÇÃO ---

# KPI Cards (Sem Emojis)
val_final = df_results.iloc[-1]["Prevalência (%)"]
total_cost = df_results["Custo Saúde (Bilhões R$)"].sum()
delta_prev = val_final - (prevalence_initial * 100)

col1, col2, col3 = st.columns(3)
col1.metric("Prevalência Final (2041)", f"{val_final:.2f}%", delta=f"{delta_prev:.2f} p.p.", delta_color="inverse")
col2.metric("Custo Acumulado SUS", f"R$ {total_cost:.1f} Bi")
col3.metric("Cenário Tributário", f"+{tax_hike}%")

st.divider()

# Gráficos (Sem Emojis nos Títulos)
tab1, tab2, tab3 = st.tabs(["Prevalência (%)", "Custo Econômico (R$)", "Dinâmica de Estoques"])

with tab1:
    st.subheader("Trajetória da Prevalência de Tabagismo")
    st.line_chart(df_results, x="Ano", y="Prevalência (%)", color="#2E86C1")

with tab2:
    st.subheader("Custo Direto Estimado (DCNTs)")
    st.bar_chart(df_results, x="Ano", y="Custo Saúde (Bilhões R$)", color="#884EA0")

with tab3:
    st.subheader("População por Categoria (Milhões)")
    st.area_chart(df_results, x="Ano", y=["Fumantes (M)", "Ex-Fumantes (M)"], color=["#E74C3C", "#27AE60"])

# --- RODAPÉ MATEMÁTICO (Onde você gosta) ---
st.divider()

with st.expander("Ver Lógica Matemática (SimSmoke Logic & Markov Chain)"):
    st.markdown("""
    O modelo utiliza uma **Cadeia de Markov** de 3 estados para estimar os fluxos populacionais.
    A intervenção política altera as taxas de transição baseada na elasticidade-preço da demanda.
    """)
    
    # A Matriz de Transição (Visual Acadêmico)
    st.latex(r'''
    \begin{bmatrix} N_{t+1} \\ S_{t+1} \\ E_{t+1} \end{bmatrix} = 
    \begin{bmatrix} 
    1 - \alpha & 0 & 0 \\ 
    \alpha & 1 - \gamma & \rho \\ 
    0 & \gamma & 1 - \rho 
    \end{bmatrix} \times 
    \begin{bmatrix} N_t \\ S_t \\ E_t \end{bmatrix}
    ''')
    
    st.markdown("**Equação de Diferenças (Dinâmica do Estoque de Fumantes):**")
    st.latex(r'''
    S_{t+1} = S_t - (S_t \times \gamma) + (N_t \times \alpha) + (E_t \times \rho)
    ''')
    
    st.markdown(f"""
    **Parâmetros Calibrados no Cenário Atual:**
    * $\\alpha$ (Taxa de Iniciação): **{final_init:.4f}**
    * $\\gamma$ (Taxa de Cessação): **{final_cess:.4f}**
    * $\\rho$ (Taxa de Recaída): **{final_rel:.4f}**
    """)