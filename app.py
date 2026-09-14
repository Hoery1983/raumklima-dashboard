import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Seiten-Layout auf volle Breite setzen
st.set_page_config(page_title="Raumklima Dashboard", layout="wide")
st.title("🌡️ Raumklima Dashboard")

# Datei-Upload-Feld für den Multi-Upload
uploaded_files = st.file_uploader("Lade eine oder mehrere CSV-Dateien hoch", type="csv", accept_multiple_files=True)

if uploaded_files:
    # 1. Daten einlesen, zusammenfügen und bereinigen
    df_list = [pd.read_csv(file) for file in uploaded_files]
    df = pd.concat(df_list, ignore_index=True)
    
    df['Zeit'] = pd.to_datetime(df['Zeit'])
    df = df.sort_values('Zeit').drop_duplicates(subset=['Zeit']).reset_index(drop=True)
    df['Datum'] = df['Zeit'].dt.date
    
    # 2. STATUS-ALARM (Ampelsystem für den allerletzten Wert)
    aktuelle_feuchte = df['Relative Luftfeuchtigkeit_Prozentsatz'].iloc[-1]
    aktuelle_temp = df['Temperatur_Celsius'].iloc[-1]
    
    if aktuelle_feuchte >= 65:
        st.error(f"⚠️ Achtung: Die aktuelle Luftfeuchtigkeit liegt bei {aktuelle_feuchte} %. Es besteht akute Schimmelgefahr. Bitte dringend stoßlüften!")
    elif aktuelle_feuchte >= 60:
        st.warning(f"⚡ Hinweis: Die Luftfeuchtigkeit ist mit {aktuelle_feuchte} % leicht erhöht. Ein wenig lüften wäre gut.")
    else:
        st.success(f"✅ Das aktuelle Raumklima ist optimal (Feuchtigkeit: {aktuelle_feuchte} %).")

    st.divider()

    # 3. KPI-KACHELN (Wie im Excel-Dashboard)
    st.subheader("📊 Gesamtübersicht")
    
    overall_avg_temp = df['Temperatur_Celsius'].mean()
    overall_min_temp = df['Temperatur_Celsius'].min()
    overall_max_temp = df['Temperatur_Celsius'].max()
    
    overall_avg_hum = df['Relative Luftfeuchtigkeit_Prozentsatz'].mean()
    overall_min_hum = df['Relative Luftfeuchtigkeit_Prozentsatz'].min()
    overall_max_hum = df['Relative Luftfeuchtigkeit_Prozentsatz'].max()
    
    # Erste Reihe: Temperatur
    col1, col2, col3 = st.columns(3)
    col1.metric("Aktuell Temperatur", f"{aktuelle_temp} °C")
    col2.metric("Ø Temperatur (Gesamt)", f"{overall_avg_temp:.1f} °C")
    col3.metric("Temp. Spanne (Min-Max)", f"{overall_min_temp:.1f} - {overall_max_temp:.1f} °C")
    
    # Zweite Reihe: Luftfeuchtigkeit
    col4, col5, col6 = st.columns(3)
    col4.metric("Aktuell Luftfeuchtigkeit", f"{aktuelle_feuchte} %")
    col5.metric("Ø Luftfeuchtigkeit (Gesamt)", f"{overall_avg_hum:.1f} %")
    col6.metric("Feuchte Spanne (Min-Max)", f"{overall_min_hum:.1f} - {overall_max_hum:.1f} %")
    
    st.divider()
    
    # 4. TAGESVERLAUF IM DETAIL (Mit Dropdown-Auswahl für das Datum)
    available_dates = df['Datum'].unique()
    # Der aktuellste Tag ist standardmäßig vorausgewählt
    selected_date = st.selectbox("Wähle einen Tag für den 24h-Detailverlauf aus:", available_dates, index=len(available_dates)-1)
    
    df_selected_day = df[df['Datum'] == selected_date]
    st.subheader(f"⏱️ Tagesverlauf am {selected_date.strftime('%d.%m.%Y')}")
    
    fig_detail = px.line(
        df_selected_day, 
        x='Zeit', 
        y=['Temperatur_Celsius', 'Relative Luftfeuchtigkeit_Prozentsatz'],
        labels={'value': 'Messwert', 'variable': 'Sensordaten'}
    )
    # Warnlinie bei 60% einziehen
    fig_detail.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="Warn-Grenze (60%)", annotation_position="top left")
    st.plotly_chart(fig_detail, use_container_width=True)
    
    st.divider()
    
    # 5. LANGZEIT-TRENDS (Min, Ø, Max pro Tag)
    st.subheader("📈 Langzeit-Trends (Mehrtagesvergleich)")
    
    daily_agg = df.groupby('Datum').agg(
        Min_Temp=('Temperatur_Celsius', 'min'),
        Avg_Temp=('Temperatur_Celsius', 'mean'),
        Max_Temp=('Temperatur_Celsius', 'max'),
        Min_Feuchte=('Relative Luftfeuchtigkeit_Prozentsatz', 'min'),
        Avg_Feuchte=('Relative Luftfeuchtigkeit_Prozentsatz', 'mean'),
        Max_Feuchte=('Relative Luftfeuchtigkeit_Prozentsatz', 'max')
    ).reset_index()
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(x=daily_agg['Datum'], y=daily_agg['Max_Temp'], name='Max', line=dict(color='red', dash='dot')))
        fig_temp.add_trace(go.Scatter(x=daily_agg['Datum'], y=daily_agg['Avg_Temp'], name='Ø', line=dict(color='orange', width=3)))
        fig_temp.add_trace(go.Scatter(x=daily_agg['Datum'], y=daily_agg['Min_Temp'], name='Min', line=dict(color='blue', dash='dot')))
        fig_temp.update_layout(title="Temperatur-Trend (°C)", hovermode="x unified")
        st.plotly_chart(fig_temp, use_container_width=True)
        
    with col_chart2:
        fig_hum = go.Figure()
        fig_hum.add_trace(go.Scatter(x=daily_agg['Datum'], y=daily_agg['Max_Feuchte'], name='Max', line=dict(color='darkblue', dash='dot')))
        fig_hum.add_trace(go.Scatter(x=daily_agg['Datum'], y=daily_agg['Avg_Feuchte'], name='Ø', line=dict(color='lightblue', width=3)))
        fig_hum.add_trace(go.Scatter(x=daily_agg['Datum'], y=daily_agg['Min_Feuchte'], name='Min', line=dict(color='gray', dash='dot')))
        fig_hum.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="Warn-Grenze")
        fig_hum.update_layout(title="Luftfeuchtigkeits-Trend (%)", hovermode="x unified")
        st.plotly_chart(fig_hum, use_container_width=True)