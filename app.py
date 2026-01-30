import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import io
import hashlib

st.set_page_config(page_title="Расчёт остаточного ресурса змеевиков", layout="wide")
st.title("Определение остаточного ресурса змеевиков ВРЧ")

# --- Инициализация session_state ---
if 'test_data_input' not in st.session_state:
    st.session_state.test_data_input = []
if 'widget_prefix' not in st.session_state:
    st.session_state.widget_prefix = "default"
if 'steel_grade' not in st.session_state:
    st.session_state.steel_grade = "12Х1МФ"
if 'selected_param' not in st.session_state:
    st.session_state.selected_param = "Трунина"

# --- Загрузка / сохранение проекта ---
st.sidebar.header("📁 Сохранить / загрузить проект")
uploaded_file = st.sidebar.file_uploader("Загрузите проект (.json)", type=["json"])
uploaded_excel = st.sidebar.file_uploader("Загрузите данные испытаний (.xlsx, .xls)", type=["xlsx", "xls"])
project_data = None

# Управление префиксом ключей для сброса кэша виджетов при загрузке
if uploaded_file is not None:
    try:
        project_data = json.load(uploaded_file)
        st.sidebar.success("✅ Проект загружен!")
        prefix_seed = json.dumps(project_data, sort_keys=True, ensure_ascii=False)
        st.session_state.widget_prefix = "loaded_" + str(hash(prefix_seed))[:12]
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка при загрузке: {e}")
        st.session_state.widget_prefix = "default")
else:
    pass

# --- Загрузка данных из Excel ---
if uploaded_excel is not None:
    try:
        excel_bytes = uploaded_excel.getvalue()
        
        try:
            excel_data = pd.read_excel(io.BytesIO(excel_bytes), engine='openpyxl')
        except Exception:
            try:
                excel_data = pd.read_excel(io.BytesIO(excel_bytes), engine='xlrd')
            except Exception:
                excel_data = pd.read_excel(io.BytesIO(excel_bytes))
        
        required_columns = ['Образец', 'sigma_MPa', 'T_C', 'tau_h']
        missing_columns = [col for col in required_columns if col not in excel_data.columns]
        
        if missing_columns:
            st.sidebar.error(f"❌ В файле Excel отсутствуют необходимые столбцы: {missing_columns}")
            st.sidebar.info("📋 Нужные столбцы: Образец, sigma_MPa, T_C, tau_h")
        else:
            test_data_from_excel = []
            for _, row in excel_data.iterrows():
                test_data_from_excel.append({
                    "Образец": str(row['Образец']),
                    "sigma_MPa": float(row['sigma_MPa']),
                    "T_C": float(row['T_C']),
                    "tau_h": float(row['tau_h'])
                })
            
            st.session_state.test_data_input = test_data_from_excel
            st.sidebar.success(f"✅ Загружено {len(test_data_from_excel)} испытаний из Excel")
            
            data_str = json.dumps(test_data_from_excel, sort_keys=True)
            hash_obj = hashlib.md5(data_str.encode()).hexdigest()[:12]
            st.session_state.widget_prefix = f"excel_{hash_obj}"
            
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка при чтении Excel файла: {str(e)}")

# --- Загрузка параметров или установка значений по умолчанию ---
if project_data is not None:
    loaded_test_data = project_data.get("испытания", [])
    params = project_data.get("параметры_трубы", {})
    selected_param = project_data.get("выбранный_параметр", "Трунина")
    selected_steel = project_data.get("марка_стали", "12Х1МФ")
    C_trunin_val = project_data.get("коэффициент_C_trunin", 24.88)
    C_larson_val = project_data.get("коэффициент_C_larson", 20.0)
    series_name = project_data.get("название_серии", "Образцы")
    st.session_state.test_data_input = loaded_test_data.copy()
    st.session_state.steel_grade = selected_steel
    st.session_state.selected_param = selected_param
else:
    params = {}
    selected_param = "Трунина"
    selected_steel = st.session_state.steel_grade
    series_name = "Образцы"
    if not st.session_state.test_data_input:
        st.session_state.test_data_input = [{"Образец": f"Обр.{i+1}", "sigma_MPa": 120.0, "T_C": 600.0, "tau_h": 500.0} for i in range(6)]

# --- Название серии испытаний ---
st.header("0. Название серии испытаний")
series_name = st.text_input("Введите название серии образцов", value=series_name)

# --- Выбор марки стали ---
st.header("1. Выберите марку стали")
steel_options = ["12Х1МФ", "12Х18Н12Т"]
selected_steel = st.selectbox(
    "Марка стали",
    options=steel_options,
    index=steel_options.index(selected_steel) if selected_steel in steel_options else 0
)
st.session_state.steel_grade = selected_steel

# --- Выбор типа параметра долговечности ---
st.header("2. Выберите параметр долговечности")
param_options = ["Трунина", "Ларсона-Миллера"]
selected_param = st.selectbox(
    "Тип параметра",
    options=param_options,
    index=param_options.index(selected_param) if selected_param in param_options else 0
)
st.session_state.selected_param = selected_param

# --- Автоматическая установка коэффициентов в зависимости от марки стали ---
def set_default_coefficients(steel_grade, parameter):
    if steel_grade == "12Х1МФ":
        if parameter == "Трунина":
            return 24.88
        else:
            return 20.0
    elif steel_grade == "12Х18Н12Т":
        if parameter == "Трунина":
            return 26.3
        else:
            return 20.0
    return 24.88

# Начальные значения коэффициентов по умолчанию
if project_data is None:
    C_trunin_val = set_default_coefficients(selected_steel, "Трунина")
    C_larson_val = set_default_coefficients(selected_steel, "Ларсона-Миллера")

# Применяем коэффициенты по умолчанию при изменении марки стали или параметра
if 'prev_steel' not in st.session_state:
    st.session_state.prev_steel = selected_steel
if 'prev_param' not in st.session_state:
    st.session_state.prev_param = selected_param

if (st.session_state.prev_steel != selected_steel or 
    st.session_state.prev_param != selected_param):
    default_C = set_default_coefficients(selected_steel, selected_param)
    if selected_param == "Трунина":
        C_trunin_val = default_C
    else:
        C_larson_val = default_C
    
    st.session_state.prev_steel = selected_steel
    st.session_state.prev_param = selected_param

# --- Настройка количества испытаний ---
st.header("3. Настройка количества испытаний")
num_tests = st.slider(
    "Количество испытаний (образцов)",
    min_value=0,
    max_value=100,
    value=len(st.session_state.test_data_input),
    step=1
)

# --- Синхронизация session_state с num_tests ---
if len(st.session_state.test_data_input) != num_tests:
    current = st.session_state.test_data_input
    if num_tests > len(current):
        for i in range(len(current), num_tests):
            current.append({"Образец": f"Обр.{i+1}", "sigma_MPa": 120.0, "T_C": 600.0, "tau_h": 500.0})
    else:
        current = current[:num_tests]
    st.session_state.test_data_input = current

# --- Ввод данных испытаний ---
st.header("4. Введите данные испытаний")
if num_tests > 0:
    for i in range(num_tests):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            sample = col1.text_input(
                f"Образец {i+1}",
                value=st.session_state.test_data_input[i]["Образец"],
                key=f"{st.session_state.widget_prefix}_sample_{i}"
            )
        with col2:
            sigma = col2.number_input(
                f"σ, МПа (исп. {i+1})",
                value=float(st.session_state.test_data_input[i]["sigma_MPa"]),
                min_value=0.1,
                max_value=500.0,
                key=f"{st.session_state.widget_prefix}_sigma_{i}"
            )
        with col3:
            T_C = col3.number_input(
                f"T, °C (исп. {i+1})",
                value=float(st.session_state.test_data_input[i]["T_C"]),
                min_value=100.0,
                max_value=1000.0,
                key=f"{st.session_state.widget_prefix}_T_{i}"
            )
        with col4:
            tau_h = col4.number_input(
                f"τ, ч (исп. {i+1})",
                value=float(st.session_state.test_data_input[i]["tau_h"]),
                min_value=1.0,
                max_value=1e7,
                key=f"{st.session_state.widget_prefix}_tau_{i}"
            )
        st.session_state.test_data_input[i] = {
            "Образец": sample,
            "sigma_MPa": sigma,
            "T_C": T_C,
            "tau_h": tau_h
        }
else:
    st.info("Нет данных испытаний. График будет построен только с кривой допускаемых напряжений.")

df_tests = pd.DataFrame(st.session_state.test_data_input) if st.session_state.test_data_input else pd.DataFrame()

# --- Ввод параметров трубы ---
st.header("5. Введите параметры трубы")
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
st.header("6. Дополнительные настройки")
col1, col2 = st.columns(2)
with col1:
    if selected_param == "Трунина":
        # Автоматически устанавливаем правильное значение для выбранной марки стали
        default_C_value = set_default_coefficients(selected_steel, selected_param)
        C = st.number_input(
            "Коэффициент C в параметре Трунина",
            value=float(default_C_value),
            min_value=0.0,
            max_value=50.0,
            format="%.3f",
            help=f"По умолчанию для {selected_steel}: {default_C_value}"
        )
    else:
        # Для параметра Ларсона-Миллера всегда 20.0 для обеих марок стали
        default_C_value = 20.0
        C = st.number_input(
            "Коэффициент C в параметре Ларсона-Миллера",
            value=float(default_C_value),
            min_value=0.0,
            max_value=50.0,
            format="%.3f",
            help=f"По умолчанию для всех марок стали: {default_C_value}"
        )
with col2:
    fig_width_cm = st.slider("Ширина графика (см)", min_value=12, max_value=20, value=17, step=1)
    fig_width_in = fig_width_cm / 2.54
    fig_height_cm = st.slider("Высота графика (см)", min_value=8, max_value=15, value=10, step=1)
    fig_height_in = fig_height_cm / 2.54

# --- Кнопка сохранения ---
if st.sidebar.button("💾 Сохранить проект"):
    data_to_save = {
        "название_серии": series_name,
        "марка_стали": selected_steel,
        "испытания": st.session_state.test_data_input,
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
        "коэффициент_C_trunin": C if selected_param == "Трунина" else 24.88,
        "коэффициент_C_larson": C if selected_param == "Ларсона-Миллера" else 20.0,
    }
    json_str = json.dumps(data_to_save, indent=2, ensure_ascii=False)
    st.sidebar.download_button(
        label="📥 Скачать проект (.json)",
        data=json_str,
        file_name="проект_ресурса.json",
        mime="application/json"
    )

# --- Шаблон Excel для скачивания ---
if st.sidebar.button("📥 Скачать шаблон Excel"):
    template_data = {
        'Образец': ['Обр.1', 'Обр.2', 'Обр.3'],
        'sigma_MPa': [120.0, 130.0, 140.0],
        'T_C': [600.0, 610.0, 620.0],
        'tau_h': [500.0, 450.0, 400.0]
    }
    template_df = pd.DataFrame(template_data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        template_df.to_excel(writer, index=False, sheet_name='Данные испытаний')
    
    st.sidebar.download_button(
        label="Скачать шаблон (.xlsx)",
        data=output.getvalue(),
        file_name="шаблон_данных_испытаний.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- Расчёт ---
if st.button("Построить график и рассчитать"):
    try:
        # --- 1. Расчет напряжений для фактического состояния ---
        # 1.1. Фактическое напряжение от давления (без запаса) - ДЛЯ ГРАФИКА
        sigma_fact_graph = (p_MPa / 2) * (d_max / s_min + 1)
        
        # 1.2. Расчетное напряжение с коэффициентом запаса - ДЛЯ ПРОВЕРКИ БЕЗОПАСНОСТИ
        sigma_rasch = k_zapas * sigma_fact_graph
        
        # 1.3. Параметр P для фактической наработки
        T_rab = T_rab_C + 273.15
        
        if selected_param == "Трунина":
            P_fact = T_rab * (np.log10(tau_exp) - 2 * np.log10(T_rab) + C) * 1e-3
        else:
            P_fact = T_rab * (np.log10(tau_exp) + C) * 1e-3
        
        # --- 2. Расчет для точек испытаний (если есть) ---
        if len(df_tests) > 0:
            df_tests["T_K"] = df_tests["T_C"] + 273.15
            
            if selected_param == "Трунина":
                df_tests["P"] = df_tests["T_K"] * (np.log10(df_tests["tau_h"]) - 2 * np.log10(df_tests["T_K"]) + C) * 1e-3
            else:
                df_tests["P"] = df_tests["T_K"] * (np.log10(df_tests["tau_h"]) + C) * 1e-3
            
            if len(df_tests) > 1:
                df_tests["group"] = df_tests["sigma_MPa"].astype(str) + "_" + df_tests["T_C"].astype(str)
                worst_df = df_tests.loc[df_tests.groupby("group")["tau_h"].idxmin()].copy()
            else:
                worst_df = df_tests.copy()
        
        # --- 3. Построение графика ---
        sigma_vals = np.linspace(20, 150, 300)
        
        # Кривая допускаемых напряжений
        if selected_steel == "12Х1МФ":
            P_dop = (24956 - 2400 * np.log10(sigma_vals) - 10.9 * sigma_vals) * 1e-3
            steel_label = f"12Х1МФ (допускаемое снижение длительной прочности)"
        elif selected_steel == "12Х18Н12Т":
            P_dop = (30942 - 3762 * np.log10(sigma_vals) - 16.8 * sigma_vals) * 1e-3
            steel_label = f"12Х18Н12Т (допускаемое снижение длительной прочности)"
        
        # Создаем график с увеличенной шириной для легенды
        fig, ax = plt.subplots(figsize=(fig_width_in, fig_height_in))
        
        # 1. Кривая допускаемых напряжений
        ax.plot(P_dop, sigma_vals, 'k-', label=steel_label, linewidth=2)
        
        # 2. Точки испытаний (если есть)
        if len(df_tests) > 0:
            ax.scatter(df_tests["P"], df_tests["sigma_MPa"], c='b', s=50, 
                      label=f'Испытания: {series_name}', alpha=0.7)
            
            if len(df_tests) > 1:
                ax.scatter(worst_df["P"], worst_df["sigma_MPa"], c='r', 
                          edgecolors='k', s=80, label='Наихудшие точки')
        
        # 3. Фактическое состояние трубы - ДВЕ ТОЧКИ
        # а) Фактическое напряжение (без запаса) - ЗЕЛЕНАЯ ТОЧКА
        ax.scatter(P_fact, sigma_fact_graph, c='green', s=120, marker='o',
                  edgecolors='black', linewidth=1.5, 
                  label=f'Факт: σ={sigma_fact_graph:.1f} МПа (без запаса)')
        
        # б) Расчетное напряжение (с запасом) - КРАСНАЯ ТОЧКА
        ax.scatter(P_fact, sigma_rasch, c='red', s=120, marker='s',
                  edgecolors='black', linewidth=1.5,
                  label=f'Расч: σ={sigma_rasch:.1f} МПа (k={k_zapas})')
        
        # Линия между фактическим и расчетным напряжением
        ax.plot([P_fact, P_fact], [sigma_fact_graph, sigma_rasch], 
               'k--', linewidth=1, alpha=0.5)
        
        # 4. Аппроксимация и рабочая точка (если есть 2+ точки)
        if len(df_tests) >= 2:
            X = worst_df["P"].values
            y = np.log10(worst_df["sigma_MPa"].values)
            A = np.vstack([X, np.ones(len(X))]).T
            a, b = np.linalg.lstsq(A, y, rcond=None)[0]
            R2 = 1 - np.sum((y - (a*X + b))**2) / np.sum((y - np.mean(y))**2)
            
            P_appr = (np.log10(sigma_vals) - b) / a
            ax.plot(P_appr, sigma_vals, 'r--', 
                   label=f'Аппроксимация (R²={R2:.3f})', linewidth=1.5)
        
        # Настройка графика
        ax.set_xlim(P_dop.min() - 0.1, P_dop.max() + 0.1)
        ax.set_ylim(20, 150)
        
        if selected_param == "Трунина":
            xlabel_text = f"Параметр Трунина $P = T \\cdot (\\log_{{10}}(\\tau) - 2\\log_{{10}}(T) + {C:.2f}) \\cdot 10^{{-3}}$"
        else:
            xlabel_text = f"Параметр Ларсона-Миллера $P = T \\cdot (\\log_{{10}}(\\tau) + {C:.2f}) \\cdot 10^{{-3}}$"
        
        ax.set_xlabel(xlabel_text, fontsize=10)
        ax.set_ylabel(r"$\sigma$, МПа", fontsize=11)
        ax.set_title(f"Длительная прочность стали {selected_steel}", fontsize=12, pad=15)
        
        # Легенда справа от графика
        ax.legend(fontsize=9, frameon=True, fancybox=True, 
                 shadow=True, framealpha=0.9, 
                 bbox_to_anchor=(1.05, 1), loc='upper left')
        
        ax.grid(True, alpha=0.3)
        
        # Увеличиваем правый отступ для легенды
        plt.subplots_adjust(right=0.75)
        
        st.pyplot(fig, use_container_width=False)
        
        # --- 4. Результаты расчетов ---
        st.header("Результаты расчетов")
        
        # Находим допускаемое напряжение для P_fact
        idx = np.argmin(np.abs(P_dop - P_fact))
        sigma_dop = sigma_vals[idx]
        
        # Расчет запасов
        margin_fact = (sigma_dop / sigma_fact_graph - 1) * 100
        margin_rasch = (sigma_dop / sigma_rasch - 1) * 100
        
        # Таблица с результатами
        results_data = {
            "Параметр": [
                "Давление p",
                "Макс. диаметр d_max",
                "Мин. толщина s_min",
                "Формула для σ_факт",
                "σ_факт (без запаса)",
                "Коэффициент запаса k_зап",
                "σ_расч (с запасом)",
                "Допускаемое напряжение σ_доп",
                "Запас по σ_факт",
                "Запас по σ_расч",
                "Рабочая температура T_раб",
                "Наработка τ_э",
                "Параметр P",
                "Марка стали",
                "Параметр долговечности",
                "Коэффициент C"
            ],
            "Значение": [
                f"{p_MPa:.2f} МПа",
                f"{d_max:.2f} мм",
                f"{s_min:.3f} мм",
                f"σ = (p/2) × (d/s + 1)",
                f"{sigma_fact_graph:.1f} МПа",
                f"{k_zapas:.1f}",
                f"{sigma_rasch:.1f} МПа",
                f"{sigma_dop:.1f} МПа",
                f"{margin_fact:.1f}%" + (" ✅" if margin_fact > 0 else " ⚠️"),
                f"{margin_rasch:.1f}%" + (" ✅" if margin_rasch > 0 else " ⚠️"),
                f"{T_rab_C:.1f} °C ({T_rab:.1f} K)",
                f"{tau_exp:,} ч",
                f"{P_fact:.4f}",
                selected_steel,
                selected_param,
                f"{C:.2f}"
            ]
        }
        
        results_df = pd.DataFrame(results_data)
        st.table(results_df)
        
        # Анализ безопасности
        st.subheader("Анализ безопасности")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**По фактическому напряжению (без запаса):**")
            if margin_fact > 0:
                st.success(f"✅ Безопасно")
                st.write(f"Запас: {margin_fact:.1f}%")
                st.write(f"σ_факт ({sigma_fact_graph:.1f} МПа) < σ_доп ({sigma_dop:.1f} МПа)")
            else:
                st.error(f"⚠️ Опасно!")
                st.write(f"Превышение: {abs(margin_fact):.1f}%")
                st.write(f"σ_факт ({sigma_fact_graph:.1f} МПа) > σ_доп ({sigma_dop:.1f} МПа)")
        
        with col2:
            st.write(f"**По расчетному напряжению (с запасом k={k_zapas}):**")
            if margin_rasch > 0:
                st.success(f"✅ Безопасно")
                st.write(f"Запас: {margin_rasch:.1f}%")
                st.write(f"σ_расч ({sigma_rasch:.1f} МПа) < σ_доп ({sigma_dop:.1f} МПа)")
            else:
                st.error(f"⚠️ Опасно!")
                st.write(f"Превышение: {abs(margin_rasch):.1f}%")
                st.write(f"σ_расч ({sigma_rasch:.1f} МПа) > σ_доп ({sigma_dop:.1f} МПа)")
        
        # --- 5. Расчет остаточного ресурса (если 2+ точки) ---
        if len(df_tests) >= 2:
            st.header("Расчет остаточного ресурса")
            
            # Скорость коррозии
            if s_max > s_nom:
                v_corr = (s_max - s_min) / tau_exp
            else:
                v_corr = (s_nom - s_min) / tau_exp
            
            # Итерационный расчет
            def calculate_tau_r(tau_guess):
                s_min2 = s_min - v_corr * tau_guess
                if s_min2 <= 0:
                    return np.inf, 0, 0
                
                # Напряжение для будущего состояния
                sigma_k2 = (p_MPa / 2) * (d_max / s_min2 + 1)
                sigma_rasch2 = k_zapas * sigma_k2
                P_rab = (np.log10(sigma_rasch2) - b) / a
                
                if selected_param == "Трунина":
                    log_tau_r = P_rab / T_rab * 1000 + 2 * np.log10(T_rab) - C
                else:
                    log_tau_r = P_rab / T_rab * 1000 - C
                
                tau_r = 10**log_tau_r
                return tau_r, sigma_rasch2, s_min2
            
            tau_prognoz = 50000.0
            converged = False
            iteration_data = []
            
            for iter_num in range(100):
                tau_r, sigma_rasch2, s_min2 = calculate_tau_r(tau_prognoz)
                
                iteration_data.append({
                    "Итерация": iter_num + 1,
                    "τ_прогн, ч": round(tau_prognoz, 0),
                    "τ_р, ч": round(tau_r, 0),
                    "Разница, ч": round(tau_prognoz - tau_r, 0),
                    "s_min2, мм": round(s_min2, 3)
                })
                
                if not np.isfinite(tau_r) or tau_r <= 0:
                    break
                
                delta = tau_prognoz - tau_r
                if abs(delta) <= 200:
                    converged = True
                    break
                
                correction = delta * 0.5
                correction = np.clip(correction, -10000, 10000)
                tau_prognoz = tau_prognoz - correction
                
                if tau_prognoz <= 0:
                    tau_prognoz = 1000
            
            # Финальный расчет
            tau_r_final, sigma_rasch_final, s_min2_final = calculate_tau_r(tau_prognoz)
            delta_final = tau_prognoz - tau_r_final
            
            if converged:
                st.success(f"✅ **Остаточный ресурс: {tau_prognoz:,.0f} ч**")
                
                # Таблица итераций
                if len(iteration_data) > 0:
                    with st.expander("Показать процесс итераций"):
                        st.table(pd.DataFrame(iteration_data))
                
                # Результаты прогноза
                forecast_data = {
                    "Параметр": [
                        "Остаточный ресурс τ_прогн",
                        "Время до разрушения τ_р",
                        "Разница (τ_прогн - τ_р)",
                        "Минимальная толщина после ресурса",
                        "Напряжение после ресурса (с запасом)",
                        "Скорость коррозии",
                        "Коэффициент аппроксимации a",
                        "Коэффициент аппроксимации b",
                        "R² аппроксимации"
                    ],
                    "Значение": [
                        f"{tau_prognoz:,.0f} ч",
                        f"{tau_r_final:,.0f} ч",
                        f"{delta_final:.0f} ч",
                        f"{s_min2_final:.3f} мм",
                        f"{sigma_rasch_final:.1f} МПа",
                        f"{v_corr:.6f} мм/ч",
                        f"{a:.4f}",
                        f"{b:.4f}",
                        f"{R2:.4f}"
                    ]
                }
                
                forecast_df = pd.DataFrame(forecast_data)
                st.table(forecast_df)
            else:
                st.warning("Не удалось достичь сходимости в расчете остаточного ресурса.")
                if len(iteration_data) > 0:
                    with st.expander("Показать процесс итераций"):
                        st.table(pd.DataFrame(iteration_data))
        else:
            st.info("""
            **Для расчета остаточного ресурса необходимо как минимум 2 точки испытаний.**
            
            Сейчас на графике отображены:
            1. Кривая допускаемых напряжений для выбранной марки стали
            2. Фактическое напряжение в трубе (зеленый круг)
            3. Расчетное напряжение с коэффициентом запаса (красный квадрат)
            4. Точки испытаний (если есть)
            
            Вы можете:
            - Добавить больше точек испытаний
            - Изменить параметры трубы
            - Сравнить положение точек относительно кривой допускаемых напряжений
            """)
            
    except Exception as e:
        st.error(f"Ошибка: {str(e)[:200]}")
        import traceback
        st.text(traceback.format_exc())
