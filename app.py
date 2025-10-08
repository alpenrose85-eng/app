import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json

st.set_page_config(page_title="Расчёт остаточного ресурса змеевиков", layout="wide")
st.title("Определение остаточного ресурса змеевиков ВРЧ")

# --- Инициализация session_state ---
if 'test_data_input' not in st.session_state:
    st.session_state.test_data_input = []

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

# --- Загрузка параметров или установка значений по умолчанию ---
if project_data is not None:
    loaded_test_data = project_data.get("испытания", [])
    num_tests_from_file = len(loaded_test_data)
    params = project_data.get("параметры_трубы", {})
    selected_param = project_data.get("выбранный_параметр", "Трунина")
    C_trunin_val = project_data.get("коэффициент_C_trunin", 24.88)
    C_larson_val = project_data.get("коэффициент_C_larson", 20.0)
    series_name = project_data.get("название_серии", "Образцы")
    # Обновляем session_state
    st.session_state.test_data_input = loaded_test_data.copy()
else:
    params = {}
    num_tests_from_file = 6
    selected_param = "Трунина"
    C_trunin_val = 24.88
    C_larson_val = 20.0
    series_name = "Образцы"
    # Инициализируем пустыми или дефолтными
    if not st.session_state.test_data_input:
        st.session_state.test_data_input = [{"Образец": f"Обр.{i+1}", "sigma_MPa": 120.0, "T_C": 600.0, "tau_h": 500.0} for i in range(num_tests_from_file)]

# --- Название серии испытаний ---
st.header("0. Название серии испытаний")
series_name = st.text_input("Введите название серии образцов", value=series_name)

# --- Выбор типа параметра долговечности ---
st.header("1. Выберите параметр долговечности")
param_options = ["Трунина", "Ларсона-Миллера"]
selected_param = st.selectbox(
    "Тип параметра",
    options=param_options,
    index=param_options.index(selected_param) if selected_param in param_options else 0
)

# --- Настройка количества испытаний ---
st.header("2. Настройка количества испытаний")
num_tests = st.slider(
    "Количество испытаний (образцов)",
    min_value=1,
    max_value=100,
    value=len(st.session_state.test_data_input),
    step=1
)

# --- Синхронизация session_state с num_tests ---
if len(st.session_state.test_data_input) != num_tests:
    current = st.session_state.test_data_input
    if num_tests > len(current):
        # Добавляем новые
        for i in range(len(current), num_tests):
            current.append({"Образец": f"Обр.{i+1}", "sigma_MPa": 120.0, "T_C": 600.0, "tau_h": 500.0})
    else:
        # Обрезаем
        current = current[:num_tests]
    st.session_state.test_data_input = current

# --- Ввод данных испытаний ---
st.header("3. Введите данные испытаний")
for i in range(num_tests):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sample = col1.text_input(
            f"Образец {i+1}",
            value=st.session_state.test_data_input[i]["Образец"],
            key=f"sample_{i}"
        )
    with col2:
        sigma = col2.number_input(
            f"σ, МПа (исп. {i+1})",
            value=float(st.session_state.test_data_input[i]["sigma_MPa"]),
            min_value=0.1,
            max_value=500.0,
            key=f"sigma_{i}"
        )
    with col3:
        T_C = col3.number_input(
            f"T, °C (исп. {i+1})",
            value=float(st.session_state.test_data_input[i]["T_C"]),
            min_value=100.0,
            max_value=1000.0,
            key=f"T_{i}"
        )
    with col4:
        tau_h = col4.number_input(
            f"τ, ч (исп. {i+1})",
            value=float(st.session_state.test_data_input[i]["tau_h"]),
            min_value=1.0,
            max_value=1e7,
            key=f"tau_{i}"
        )
    # Обновляем session_state
    st.session_state.test_data_input[i] = {
        "Образец": sample,
        "sigma_MPa": sigma,
        "T_C": T_C,
        "tau_h": tau_h
    }

df_tests = pd.DataFrame(st.session_state.test_data_input)

# --- Ввод параметров трубы ---
st.header("4. Введите параметры трубы")
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

# --- Настройка коэффициентов и графика ---
st.header("5. Дополнительные настройки")
col1, col2 = st.columns(2)
with col1:
    if selected_param == "Трунина":
        C = st.number_input(
            "Коэффициент C в параметре Трунина",
            value=float(C_trunin_val),
            min_value=0.0,
            max_value=50.0,
            format="%.3f"
        )
    else:  # Ларсона-Миллера
        C = st.number_input(
            "Коэффициент C в параметре Ларсона-Миллера",
            value=float(C_larson_val),
            min_value=0.0,
            max_value=50.0,
            format="%.3f"
        )
with col2:
    fig_width_cm = st.slider("Ширина графика (см)", min_value=12, max_value=17, value=15, step=1)
    fig_width_in = fig_width_cm / 2.54
    fig_height_cm = st.slider("Высота графика (см)", min_value=8, max_value=12, value=10, step=1)
    fig_height_in = fig_height_cm / 2.54

# --- Кнопка сохранения ---
if st.sidebar.button("💾 Сохранить проект"):
    data_to_save = {
        "название_серии": series_name,
        "испытания": st.session_state.test_data_input,  # ✅ Гарантированно актуальные данные
        "параметры_трубы": {
            "s_nom": s_nom,
            "s_min": s_min,
            "s_max": s_max,
            "tau_exp": tau_exp,
            "d_max": d_max,
            "T_rab_C": T_rab_C,
            "p_MPa": p_MPa,
            "k_zapas": k_zapas
        },
        "выбранный_параметр": selected_param,
        "коэффициент_C_trunin": C if selected_param == "Трунина" else C_trunin_val,
        "коэффициент_C_larson": C if selected_param == "Ларсона-Миллера" else C_larson_val,
    }
    json_str = json.dumps(data_to_save, indent=2, ensure_ascii=False)
    st.sidebar.download_button(
        label="📥 Скачать проект (.json)",
        data=json_str,
        file_name="проект_ресурса.json",
        mime="application/json"
    )

# --- Расчёт ---
if st.button("Рассчитать остаточный ресурс"):
    try:
        if len(df_tests) < 2:
            st.error("❌ Для аппроксимации необходимо минимум 2 точки испытаний.")
        else:
            # --- 1. Расчёт P в зависимости от выбранного параметра ---
            df_tests["T_K"] = df_tests["T_C"] + 273.15
            if selected_param == "Трунина":
                df_tests["P"] = df_tests["T_K"] * (np.log10(df_tests["tau_h"]) - 2 * np.log10(df_tests["T_K"]) + C) * 1e-3
            else:  # Ларсона-Миллера
                df_tests["P"] = df_tests["T_K"] * (np.log10(df_tests["tau_h"]) + C) * 1e-3

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
            
            def calculate_tau_r(tau_guess):
                s_min2 = s_min - v_corr * tau_guess
                if s_min2 <= 0:
                    return np.inf
                sigma_k2 = (p_MPa / 2) * (d_max / s_min2 + 1)
                sigma_rasch = k_zapas * sigma_k2
                P_rab = (np.log10(sigma_rasch) - b) / a
                if selected_param == "Трунина":
                    log_tau_r = P_rab / T_rab * 1000 + 2 * np.log10(T_rab) - C
                else:
                    log_tau_r = P_rab / T_rab * 1000 - C
                tau_r = 10**log_tau_r
                return tau_r

            tau_prognoz = 50000.0
            converged = False
            max_iter = 100
            tolerance = 200.0

            for iter_num in range(max_iter):
                tau_r = calculate_tau_r(tau_prognoz)
                if not np.isfinite(tau_r) or tau_r <= 0:
                    break
                delta = tau_prognoz - tau_r
                if abs(delta) <= tolerance:
                    converged = True
                    break
                learning_rate = 0.5
                correction = delta * learning_rate
                max_step = 10000.0
                correction = np.clip(correction, -max_step, max_step)
                tau_prognoz_new = tau_prognoz - correction
                if tau_prognoz_new <= 0:
                    tau_prognoz_new = tau_prognoz / 2.0
                tau_prognoz = tau_prognoz_new

            s_min2_final = s_min - v_corr * tau_prognoz
            sigma_k2_final = (p_MPa / 2) * (d_max / s_min2_final + 1)
            sigma_rasch_final = k_zapas * sigma_k2_final
            tau_r_final = calculate_tau_r(tau_prognoz)
            delta_final = tau_prognoz - tau_r_final

            # --- 6. График ---
            sigma_vals = np.linspace(20, 150, 300)
            P_dop = (24956 - 2400 * np.log10(sigma_vals) - 10.9 * sigma_vals) * 1e-3
            P_appr = (np.log10(sigma_vals) - b) / a

            P_min = min(P_dop.min(), df_tests["P"].min(), P_appr.min())
            P_max = max(P_dop.max(), df_tests["P"].max(), P_appr.max())

            plt.figure(figsize=(fig_width_in, fig_height_in))
            plt.plot(P_dop, sigma_vals, 'k-', label='Допускаемое снижение длительной прочности')
            plt.plot(P_appr, sigma_vals, 'r--', label=f'Аппроксимация (R² = {R2:.3f})')
            plt.scatter(df_tests["P"], df_tests["sigma_MPa"], c='b', label=series_name)
            plt.scatter(worst_df["P"], worst_df["sigma_MPa"], c='r', edgecolors='k', s=80, label='Наихудшее состояние')

            plt.xlim(P_min - 0.2, P_max + 0.2)
            plt.ylim(20, 150)
            
            if selected_param == "Трунина":
                xlabel_text = f"$P = T \\cdot (\\log_{{10}}(\\tau) - 2\\log_{{10}}(T) + {C:.2f}) \\cdot 10^{{-3}}$"
            else:
                xlabel_text = f"Параметр Ларсона-Миллера $P = T \\cdot (\\log_{{10}}(\\tau) + {C:.2f}) \\cdot 10^{{-3}}$"
            
            plt.xlabel(xlabel_text)
            plt.ylabel(r"$\sigma$, МПа")
            
            plt.legend(
                fontsize='small',
                frameon=True,
                fancybox=True,
                loc='best',
                handlelength=2.5,
                handletextpad=0.5
            )
            plt.grid(True)

            st.header("Результаты расчёта")
            if converged:
                st.success(f"✅ **Остаточный ресурс: {tau_prognoz:,.0f} ч**")
                st.write(f"- Использован параметр: **{selected_param}**")
                st.write(f"- Уравнение аппроксимации: **{уравнение}**")
                st.write(f"- Расчётное напряжение с запасом: **{sigma_rasch_final:.1f} МПа**")
                st.write(f"- Мин. толщина после ресурса: **{s_min2_final:.3f} мм**")
                st.write(f"- Время до разрушения по модели: **{tau_r_final:,.0f} ч**")
                st.write(f"- Разница (τ_прогн - τ_р): **{delta_final:.0f} ч**")
                st.write(f"- Использован коэффициент C: **{C:.3f}**")
                st.write(f"- Серия образцов: **{series_name}**")
            else:
                st.error("❌ Не удалось достичь сходимости. Попробуйте другие параметры.")

            st.pyplot(plt, use_container_width=False)

    except Exception as e:
        st.error(f"Произошла ошибка: {e}")
