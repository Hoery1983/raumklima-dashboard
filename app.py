import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Seiten-Layout auf volle Breite setzen
st.set_page_config(page_title="Raumklima Dashboard", layout="wide")
st.title("🌡️ Raumklima Dashboard (Multi-Room)")

# Datei-Upload-Feld für den Multi-Upload
uploaded_files = st.file_uploader("Lade die CSV-Dateien aller Räume hier hoch", type="csv", accept_multiple_files=True)

if uploaded_files:
    # 1. Daten einlesen, Raum zuordnen und in einen großen Datensatz packen
    df_list = []
    
    for file in uploaded_files:
        filename = file.name
        if " 2_" in filename:
            raum_name = "Schlafzimmer"
        elif " 3_" in filename:
            raum_name = "Esszimmer"
        else:
            raum_name = "Wohnzimmer"
            
        temp_df = pd.read_csv(file)
        temp_df['Raum'] = raum_name
        df_list.append(temp_df)
        
    df = pd.concat(df_list, ignore_index=True)
    
    # Datum und Zeit formatieren & bereinigen
    df['Zeit'] = pd.to_datetime(df['Zeit'])
    df = df.sort_values('Zeit').drop_duplicates(subset=['Zeit', 'Raum']).reset_index(drop=True)
    df['Datum'] = df['Zeit'].dt.date
    
    st.divider()

    # --- 2. DIE REITER (TABS) FÜR DIE RÄUME AUFBAUEN ---
    # NEU: Gesamtübersicht als ersten Reiter hinzugefügt
    tab_gesamt, tab_wohn, tab_schlaf, tab_ess = st.tabs(["🏠 Haus-Übersicht", "🛋️ Wohnzimmer", "🛏️ Schlafzimmer", "🍽️ Esszimmer"])
    
    # --- HILFSFUNKTION: GESAMTÜBERSICHT (HAUS-VERGLEICH) ---
    def render_gesamt_dashboard():
        st.subheader("🏠 Live-Snapshot (Aktuellste Messwerte)")
        
        # Von jedem Raum den allerletzten Datensatz holen
        latest_records = df.sort_values('Zeit').groupby('Raum').tail(1)
        rooms_available = latest_records['Raum'].tolist()
        
        # Spalten dynamisch anhand der hochgeladenen Räume erstellen
        cols = st.columns(len(rooms_available))
        
        for idx, raum in enumerate(rooms_available):
            row = latest_records[latest_records['Raum'] == raum].iloc[0]
            temp = row['Temperatur_Celsius']
            hum = row['Relative Luftfeuchtigkeit_Prozentsatz']
            
            with cols[idx]:
                st.markdown(f"**{raum}**")
                # Wir geben der Luftfeuchtigkeit eine Warnfarbe, falls sie zu hoch ist
                hum_color = "🔴 " if hum >= 60 else "🟢 "
                st.metric("Temperatur", f"{temp} °C")
                st.metric("Luftfeuchtigkeit", f"{hum_color}{hum} %")
                
        st.divider()
        
        st.subheader("⚠️ Schimmel-Risiko-Ranking")
        st.write("Wie viel Prozent der gemessenen Zeit lag die Luftfeuchtigkeit über der kritischen 60%-Marke?")
        
        # Berechnung: %-Anteil der Werte >= 60% pro Raum
        risk_data = []
        for raum in df['Raum'].unique():
            df_r = df[df['Raum'] == raum]
            total = len(df_r)
            critical = len(df_r[df_r['Relative Luftfeuchtigkeit_Prozentsatz'] >= 60])
            risk_pct = (critical / total) * 100 if total > 0 else 0
            risk_data.append({'Raum': raum, 'Risiko (%)': round(risk_pct, 1)})
            
        df_risk = pd.DataFrame(risk_data).sort_values('Risiko (%)', ascending=True)
        
        fig_risk = px.bar(
            df_risk, x='Risiko (%)', y='Raum', orientation='h', 
            text='Risiko (%)', color='Risiko (%)', 
            color_continuous_scale='RdYlGn_r', range_color=[0, 100]
        )
        fig_risk.update_traces(texttemplate='%{text}%', textposition='outside')
        fig_risk.update_layout(xaxis_title="Zeit über 60% Feuchtigkeit (in Prozent)", yaxis_title="")
        st.plotly_chart(fig_risk, use_container_width=True)
        
        st.divider()
        
        st.subheader("📈 Synchronvergleich (Tagesdurchschnitte)")
        st.write("Alle Räume im direkten Vergleich (Linien anklicken zum Ein-/Ausblenden)")
        
        daily_raum = df.groupby(['Datum', 'Raum']).agg(
            Avg_Temp=('Temperatur_Celsius', 'mean'),
            Avg_Hum=('Relative Luftfeuchtigkeit_Prozentsatz', 'mean')
        ).reset_index()
        
        col_sync1, col_sync2 = st.columns(2)
        
        with col_sync1:
            fig_sync_temp = px.line(daily_raum, x='Datum', y='Avg_Temp', color='Raum', markers=True)
            fig_sync_temp.update_layout(title="Ø Temperatur im Haus", hovermode="x unified")
            st.plotly_chart(fig_sync_temp, use_container_width=True)
            
        with col_sync2:
            fig_sync_hum = px.line(daily_raum, x='Datum', y='Avg_Hum', color='Raum', markers=True)
            fig_sync_hum.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="Warn-Grenze")
            fig_sync_hum.update_layout(title="Ø Luftfeuchtigkeit im Haus", hovermode="x unified")
            st.plotly_chart(fig_sync_hum, use_container_width=True)


    # --- HILFSFUNKTION: EINZELRAUM-DASHBOARD (Unverändert) ---
    def render_dashboard_for_room(raum_name):
        df_raum = df[df['Raum'] == raum_name].copy()
        
        if df_raum.empty:
            st.info(f"Für das {raum_name} wurden noch keine Daten hochgeladen.")
            return

        aktuelle_feuchte = df_raum['Relative Luftfeuchtigkeit_Prozentsatz'].iloc[-1]
        aktuelle_temp = df_raum['Temperatur_Celsius'].iloc[-1]
        
        if aktuelle_feuchte >= 65:
            st.error(f"⚠️ Achtung: Akute Schimmelgefahr. Bitte stoßlüften!")
        elif aktuelle_feuchte >= 60:
            st.warning(f"⚡ Hinweis: Luftfeuchtigkeit leicht erhöht. Ein wenig lüften wäre gut.")
        else:
            st.success(f"✅ Das Klima ist optimal.")

        st.subheader("📊 Gesamtübersicht")
        
        overall_avg_temp = df_raum['Temperatur_Celsius'].mean()
        overall_min_temp = df_raum['Temperatur_Celsius'].min()
        overall_max_temp = df_raum['Temperatur_Celsius'].max()
        
        overall_avg_hum = df_raum['Relative Luftfeuchtigkeit_Prozentsatz'].mean()
        overall_min_hum = df_raum['Relative Luftfeuchtigkeit_Prozentsatz'].min()
        overall_max_hum = df_raum['Relative Luftfeuchtigkeit_Prozentsatz'].max()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Aktuell Temperatur", f"{aktuelle_temp} °C")
        col2.metric("Ø Temperatur (Gesamt)", f"{overall_avg_temp:.1f} °C")
        col3.metric("Temp. Spanne (Min-Max)", f"{overall_min_temp:.1f} - {overall_max_temp:.1f} °C")
        
        col4, col5, col6 = st.columns(3)
        col4.metric("Aktuell Luftfeuchtigkeit", f"{aktuelle_feuchte} %")
        col5.metric("Ø Luftfeuchtigkeit (Gesamt)", f"{overall_avg_hum:.1f} %")
        col6.metric("Feuchte Spanne (Min-Max)", f"{overall_min_hum:.1f} - {overall_max_hum:.1f} %")
        
        st.divider()
        
        available_dates = df_raum['Datum'].unique()
        selected_date = st.selectbox(f"Wähle einen Tag für das {raum_name}:", available_dates, index=len(available_dates)-1, key=f"date_picker_{raum_name}")
        
        df_selected_day = df_raum[df_raum['Datum'] == selected_date]
        st.subheader(f"⏱️ Tagesverlauf ({selected_date.strftime('%d.%m.%Y')})")
        
        fig_detail = px.line(df_selected_day, x='Zeit', y=['Temperatur_Celsius', 'Relative Luftfeuchtigkeit_Prozentsatz'], labels={'value': 'Messwert', 'variable': 'Sensordaten'})
        fig_detail.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="Warn-Grenze (60%)", annotation_position="top left")
        st.plotly_chart(fig_detail, use_container_width=True)
        
        st.divider()
        
        st.subheader("📈 Langzeit-Trends")
        daily_agg = df_raum.groupby('Datum').agg(
            Min_Temp=('Temperatur_Celsius', 'min'), Avg_Temp=('Temperatur_Celsius', 'mean'), Max_Temp=('Temperatur_Celsius', 'max'),
            Min_Feuchte=('Relative Luftfeuchtigkeit_Prozentsatz', 'min'), Avg_Feuchte=('Relative Luftfeuchtigkeit_Prozentsatz', 'mean'), Max_Feuchte=('Relative Luftfeuchtigkeit_Prozentsatz', 'max')
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

        st.divider()

        st.subheader("🔥 Heatmap: Durchschnittliche Feuchtigkeit nach Uhrzeit")
        df_heat = df_raum.copy()
        df_heat['Stunde'] = df_heat['Zeit'].dt.hour
        heatmap_pivot = df_heat.pivot_table(values='Relative Luftfeuchtigkeit_Prozentsatz', index='Datum', columns='Stunde', aggfunc='mean')
        heatmap_pivot = heatmap_pivot.reindex(columns=list(range(24)))
        
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=heatmap_pivot.values, x=heatmap_pivot.columns, y=heatmap_pivot.index,
            colorscale='RdYlGn_r', zmin=40, zmax=70, hoverongaps=False,
            hovertemplate='Datum: %{y}<br>Uhrzeit: %{x}:00 Uhr<br>Ø Feuchte: %{z:.1f} %<extra></extra>'
        ))
        fig_heatmap.update_layout(xaxis_title="Uhrzeit (Stunde)", yaxis_title="Datum", xaxis=dict(tickmode='linear', tick0=0, dtick=1), yaxis_autorange='reversed', height=max(400, 200 + (len(heatmap_pivot) * 15)))
        st.plotly_chart(fig_heatmap, use_container_width=True)

    # --- DIE REITER MIT INHALT FÜLLEN ---
    with tab_gesamt:
        render_gesamt_dashboard()

    with tab_wohn:
        render_dashboard_for_room("Wohnzimmer")
        
    with tab_schlaf:
        render_dashboard_for_room("Schlafzimmer")
        
    with tab_ess:
        render_dashboard_for_room("Esszimmer")
