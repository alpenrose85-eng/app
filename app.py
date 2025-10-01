import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json

st.set_page_config(page_title="Расчёт остаточного ресурса змеевиков", layout="wide")
st.title("Определение остаточного ресурса змеевиков ВРЧ")

# --- Загрузка / сохранение проекта ---
st.sidebar.header("📁 Сохранить / загрузить проект")
uploaded_file = st.sidebar.file_uploader("Загрузите проект (.json)", type=["json"])
project_data = None

if uploaded_file is not None:
    try:
        project_data = json.load(uploaded_file)
        st.sidebar.success("✅ Проект загружен!")
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка при загрузке: {e}")

# --- Ввод данных с поддержкой загрузки ---
if project_data is not None:
    test_data = project_data.get("испытания", [])
    params = project_data.get("параметры_трубы", {})
    num_tests = len(test_data)
else:
    num_tests = 6
    test_data = []
    params = {}

st.header("1. Введите данные испытаний")
test_data_input = []
for i in range(num_tests):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        default_sample = test_data[i]["Образец"] if i < len(test_data) else f"Обр.{i+1}"
        sample = col1.text_input(f"Образец {i+1}", value=str(default_sample))
    with col2:
        default_sigma = test_data[i]["sigma_MPa"] if i < len(test_data) else 120.0
        sigma = col2.number_input(f"σ, МПа (исп. {i+1})", value=float(default_sigma), min_value=0.1, max_value=500.0)
    with col3:
        default_T = test_data[i]["T_C"] if i < len(test_data) else 600.0
        T_C = col3.number_input(f"T, °C (исп. {i+1})", value=float(default_T), min_value=100.0, max_value=1000.0)
    with col4:
        default_tau = test_data[i]["tau_h"] if i < len(test_data) else 500.0
        tau_h = col4.number_input(f"τ, ч (исп. {i+1})", value=float(default_tau), min_value=1.0, max_value=1e7)
    test_data_input.append({"Образец": sample, "sigma_MPa": sigma, "T_C": T_C, "tau_h": tau_h})

df_tests = pd.DataFrame(test_data_input)

st.header("2. Введите параметры трубы")
col1, col2 = st.columns(2)
with col1:
    s_nom_val = params.get("s_nom", 6.0)
    s_nom = st.number_input("Номинальная толщина стенки s_н, мм", value=float(s_nom_val), min_value=0.1, max_value=1000.0)
    
    s_min_val = params.get("s_min", 5.07)
    s_min = st.number_input("Текущая min толщина s_мин, мм", value=float(s_min_val), min_value=0.1, max_value=s_nom)
    
    s_max_val = params.get("s_max", 5.95)
    s_max = st.number_input("Текущая max толщина s_макс, мм", value=float(s_max_val), min_value=0.1, max_value=1000.0)
    
    tau_exp_val = params.get("tau_exp", 317259)
    tau_exp = st.number_input("Наработка τ_э, ч", value=int(tau_exp_val), min_value=1, max_value=5_000_000)
with col2:
    d_max_val = params.get("d_max", 19.90)
    d_max = st.number_input("Макс. внутр. диаметр d_макс, мм", value=float(d_max_val), min_value=0.1, max_value=1000.0)
    
    T_rab_C_val = params.get("T_rab_C", 517.0)
    T_rab_C = st.number_input("Рабочая температура T_раб, °C", value=float(T_rab_C_val), min_value=100.0, max_value=1000.0)
    
    p_MPa_val = params.get("p_MPa", 27.93)
    p_MPa = st.number_input("Давление пара p, МПа", value=float(p_MPa_val), min_value=0.1, max_value=100.0)
    
    k_zapas_val = params.get("k_zapas", 1.5)
    k_zapas = st.number_input("Коэффициент запаса k_зап", value=float(k_zapas_val), min_value=1.0, max_value=5.0)

# --- Настройки графика в сантиметрах ---
st.header("3. Настройки графика (для вставки в отчёт)")
col1, col2 = st.columns(2)
with col1:
    fig_width_cm = st.slider("Ширина графика (см)", min_value=12, max_value=17, value=15, step=1)
    fig_width_in = fig_width_cm / 2.54
with col2:
    fig_height_cm = st.slider("Высота графика (см)", min_value=8, max_value=12, value=10, step=1)
    fig_height_in = fig_height_cm / 2.54

# --- Кнопка сохранения ---
if st.sidebar.button("💾 Сохранить проект"):
    data_to_save = {
        "испытания": test_data_input,
        "параметры_трубы": {
            "s_nom": s_nom,
            "s_min": s_min,
            "s_max": s_max,
            "tau_exp": tau_exp,
            "d_max": d_max,
            "T_rab_C": T_rab_C,
            "p_MPa": p_MPa,
            "k_zapas": k_zapas
        }
    }
    json_str = json.dumps(data_to_save, indent=2, ensure_ascii=False)
    st.sidebar.download_button(
        label="📥 Скачать проект (.json)",
        data=json_str,
        file_name="проект_ресурса.json",
        mime="application/json"
    )

# --- Расчёт при нажатии кнопки ---
if st.button("Рассчитать остаточный ресурс"):
    try:
        # --- 1. Расчёт P ---
        df_tests["T_K"] = df_tests["T_C"] + 273.15
        df_tests["P"] = df_tests["T_K"] * (np.log10(df_tests["tau_h"]) - 2 * np.log10(df_tests["T_K"]) + 24.88) * 1e-3

        # --- 2. Наихудшие образцы ---
        df_tests["group"] = df_tests["sigma_MPa"].astype(str) + "_" + df_tests["T_C"].astype(str)
        worst_df = df_tests.loc[df_tests.groupby("group")["tau_h"].idxmin()].copy()

        # --- 3. Аппроксимация log10(σ) = a*P + b ---
        X = worst_df["P"].values
        y = np.log10(worst_df["sigma_MPa"].values)
        A = np.vstack([X, np.ones(len(X))]).T
        a, b = np.linalg.lstsq(A, y, rcond=None)[0]
        R2 = 1 - np.sum((y - (a*X + b))**2) / np.sum((y - np.mean(y))**2)
        уравнение = f"log₁₀(σ) = {a:.3f} · P + {b:.3f}"

        # --- 4. Скорость коррозии ---
        if s_max > s_nom:
            v_corr = (s_max - s_min) / tau_exp
        else:
            v_corr = (s_nom - s_min) / tau_exp

        # --- 5. Итерационный расчёт τ_прогн ---
        T_rab = T_rab_C + 273.15
        tau_prognoz = 50000.0
        converged = False
        for iter_num in range(60):
            s_min2 = s_min - v_corr * tau_prognoz
            if s_min2 <= 0:
                st.error("❌ Толщина стенки стала ≤ 0. Проверьте данные.")
                break

            sigma_k2 = (p_MPa / 2) * (d_max / s_min2 + 1)
            sigma_rasch = k_zapas * sigma_k2

            if sigma_rasch < 20 or sigma_rasch > 150:
                st.warning(f"⚠️ Напряжение ({sigma_rasch:.1f} МПа) вне диапазона модели (20–150 МПа).")

            P_rab = (np.log10(sigma_rasch) - b) / a
            log_tau_r = P_rab / T_rab * 1000 + 2 * np.log10(T_rab) - 24.88
            tau_r = 10**log_tau_r
            delta = tau_prognoz - tau_r

            if 0 < delta <= 240:
                converged = True
                break

            if delta > 240:
                tau_prognoz *= 0.9
            else:
                tau_prognoz *= 1.1

            if iter_num > 30:
                tau_prognoz += -100 if delta > 240 else 100

        # --- 6. График ---
        sigma_vals = np.linspace(20, 150, 300)
        P_dop = (24956 - 2400 * np.log10(sigma_vals) - 10.9 * sigma_vals) * 1e-3
        P_appr = (np.log10(sigma_vals) - b) / a

        P_min = min(P_dop.min(), df_tests["P"].min(), P_appr.min())
        P_max = max(P_dop.max(), df_tests["P"].max(), P_appr.max())

        plt.figure(figsize=(fig_width_in, fig_height_in))
        plt.plot(P_dop, sigma_vals, 'k-', label='Допускаемые напряжения')
        plt.plot(P_appr, sigma_vals, 'r--', label=f'Аппроксимация (R² = {R2:.3f})')
        plt.scatter(df_tests["P"], df_tests["sigma_MPa"], c='b', label='Все точки')
        plt.scatter(worst_df["P"], worst_df["sigma_MPa"], c='r', edgecolors='k', s=80, label='Наихудшие')

        plt.xlim(P_min - 0.2, P_max + 0.2)
        plt.ylim(20, 150)
        plt.xlabel("Параметр долговечности P")
        plt.ylabel("Напряжение σ, МПа")
        plt.legend()
        plt.grid(True)

        # --- 7. Вывод результатов ---
        st.header("Результаты расчёта")
        if converged:
            st.success(f"✅ **Остаточный ресурс: {tau_prognoz:,.0f} ч**")
            st.write(f"- Уравнение аппроксимации: **{уравнение}**")
            st.write(f"- Расчётное напряжение с запасом: **{sigma_rasch:.1f} МПа**")
            st.write(f"- Мин. толщина после ресурса: **{s_min2:.3f} мм**")
            st.write(f"- Время до разрушения по модели: **{tau_r:,.0f} ч**")
            st.write(f"- Разница (τ_прогн - τ_р): **{delta:.0f} ч**")
        else:
            st.error("❌ Не удалось достичь сходимости. Попробуйте другие параметры.")

        st.pyplot(plt, use_container_width=False)

    except Exception as e:
        st.error(f"Произошла ошибка: {e}")
