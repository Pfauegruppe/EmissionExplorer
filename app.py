# Import der benötigten Bibliotheken
import streamlit as st  # Frontend-Framework für die Web-App
import pandas as pd    # Für Datenverarbeitung und -analyse
import requests        # Für HTTP-Anfragen
import plotly.express as px  # Für interaktive Visualisierungen
import numpy as np          # Für numerische Berechnungen
from geopy.geocoders import Nominatim  # Für Geocoding (Umwandlung von Adressen in Koordinaten)
from geopy.distance import geodesic    # Für Distanzberechnungen zwischen Koordinaten
from sklearn.ensemble import RandomForestRegressor  # ML-Modell für CO2-Vorhersagen
from sklearn.model_selection import train_test_split  # Für Aufteilung der Trainingsdaten
from sklearn.metrics import mean_absolute_error     # Für Modellbewertung

# Seitenkonfiguration für die Streamlit-App
st.set_page_config(
    page_title="CO2-Fussabdruck-Tracker für Reisen",  # Browser-Titel
    page_icon="🌍",    # Favicon der App
    layout="wide"      # Breites Layout für bessere Darstellung
)

# Titel und Beschreibung der App
st.title("EmissionExplorer - CO2-Fussabdruck-Tracker für Reisen")
st.markdown("""
Diese App hilft dir, den CO2-Fussabdruck deiner Reisen zu berechnen und zu visualisieren.
Vergleiche verschiedene Transportmittel und finde die umweltfreundlichste Option für deine Reiseroute!
""")

# ML-Modell-Training mit synthetischen Daten
@st.cache_data  # Ergebnisse dieser Funktion werden gecached, um Berechnungen nicht bei jedem Seiten-Refresh zu wiederholen
def train_co2_model():
    # Initialisierung der Zufallsgenerierung für reproduzierbare Ergebnisse
    np.random.seed(42)
    n_samples = 1000  # Anzahl der synthetischen Datenpunkte

    # Generierung der Eingabevariablen
    distances = np.random.uniform(10, 1000, n_samples)  # Zufällige Distanzen in km
    vehicle_ages = np.random.randint(0, 21, n_samples)  # Zufälliges Fahrzeugalter
    
    # Kategorische Variablen erstellen
    vehicle_types = np.random.choice(["Kleinwagen", "Mittelklasse", "SUV", "Luxusklasse"], n_samples)
    vehicle_type_encoded = pd.get_dummies(vehicle_types, prefix='vehicle_type')  # One-Hot-Encoding
    
    seasons = np.random.choice(["Frühling", "Sommer", "Herbst", "Winter"], n_samples)
    season_encoded = pd.get_dummies(seasons, prefix='season')  # One-Hot-Encoding
    
    traffic_levels = np.random.randint(1, 11, n_samples)  # Verkehrsaufkommen von 1-10

    # Basisemissionen pro Kilometer
    base_emissions = distances * 0.17  # Grundlegende CO2-Emissionen pro km
    
    # Einflussfaktoren auf die CO2-Emissionen
    age_factor = 1 + vehicle_ages * 0.01  
    
    type_factor = np.ones(n_samples)
    type_factor[vehicle_types == "Kleinwagen"] = 0.8    
    type_factor[vehicle_types == "Mittelklasse"] = 1.0  
    type_factor[vehicle_types == "SUV"] = 1.4           
    type_factor[vehicle_types == "Luxusklasse"] = 1.6   
    
    season_factor = np.ones(n_samples)
    season_factor[seasons == "Frühling"] = 1.0    
    season_factor[seasons == "Sommer"] = 0.95     
    season_factor[seasons == "Herbst"] = 1.05     
    season_factor[seasons == "Winter"] = 1.15  
    
    traffic_factor = 1 + (traffic_levels - 1) * 0.05    #Einfluss durch Verkehrsaufkommen
    
    # Zielwerte berechnen (CO2-Emissionen)
    co2_emissions = base_emissions * age_factor * type_factor * season_factor * traffic_factor
    
    # Rauschen hinzufügen für realistischere Daten
    co2_emissions += np.random.normal(0, 5, n_samples)
    
    # Features zusammenfügen
    X = pd.concat([
        pd.DataFrame({
            'distance': distances,
            'vehicle_age': vehicle_ages,
            'traffic_level': traffic_levels
        }),
        vehicle_type_encoded,
        season_encoded
    ], axis=1)
    
    y = co2_emissions   #Zielvariable
    
    # Trainings- und Testdaten splitten
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Modell trainieren
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Modell bewerten
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    
    # Modell und Eingabefaktoren zurückgeben
    return model, list(X.columns)

# Funktion zur Vorhersage des CO2-Fussabdrucks mit ML
def predict_co2_with_ml(distance, vehicle_age, vehicle_type, season, traffic_level, model, columns):
    # Eingabedaten für das Modell vorbereiten
    input_data = pd.DataFrame({
        'distance': [distance],
        'vehicle_age': [vehicle_age],
        'traffic_level': [traffic_level]
    })
    
    # One-hot encoding für Fahrzeugtyp
    for col in columns:
        if col.startswith('vehicle_type_'):
            vehicle_type_col = f'vehicle_type_{vehicle_type}'
            input_data[col] = 1 if col == vehicle_type_col else 0
    
    # One-hot encoding für Jahreszeit
    for col in columns:
        if col.startswith('season_'):
            season_col = f'season_{season}'
            input_data[col] = 1 if col == season_col else 0
    
    # Sicherstellen, dass alle Modell-Spalten vorhanden sind
    for col in columns:
        if col not in input_data.columns:
            input_data[col] = 0
    
    # Spalten in der richtigen Reihenfolge
    input_data = input_data[columns]
    
    # Vorhersage machen
    co2_prediction = model.predict(input_data)[0]
    
    return co2_prediction

# Modell vorab laden
model, feature_columns = train_co2_model()

# Seitenleiste für Benutzereingaben
with st.sidebar:
    st.header("Reisedetails")
    
    # Startpunkt und Ziel eingeben
    start_point = st.text_input("Startpunkt (Stadt oder Adresse)", "Zürich, Schweiz")
    end_point = st.text_input("Ziel (Stadt oder Adresse)", "Berlin, Deutschland")
    
    # Transportmittel auswählen
    transport_options = ["Auto", "Flugzeug", "Zug", "Bus", "Motorrad"]
    selected_transports = st.multiselect(
        "Wähle Transportmittel zum Vergleich",
        transport_options,
        default=["Auto", "Flugzeug", "Zug"]
    )
    
    # Anzahl der Reisenden
    travelers = st.number_input("Anzahl der Reisenden", min_value=1, value=1)
    
    # Berechnung starten
    calculate_button = st.button("CO2-Fussabdruck berechnen")
    
    # Machine Learning Abschnitt
    st.markdown("---")  #Trennlinie zur visuellen Gliederung
    st.header("Erweiterte Analyse")
    st.write("Verwende Machine Learning für präzisere CO2-Vorhersagen für Autofahrten.")
    
    # Neue Eingabeparameter für das ML-Modell
    use_ml = st.checkbox("Erweiterte CO2-Berechnung mit ML", value=False)
    
    if use_ml:   #Zusätzliche Eingabeparameter, falls ML-Modell ausgewählt wird
        vehicle_age = st.slider("Alter des Fahrzeugs (Jahre)", 0, 20, 5)
        vehicle_type = st.selectbox("Fahrzeugtyp", ["Kleinwagen", "Mittelklasse", "SUV", "Luxusklasse"])
        season = st.selectbox("Jahreszeit", ["Frühling", "Sommer", "Herbst", "Winter"])
        traffic_level = st.slider("Verkehrsaufkommen (1-10)", 1, 10, 5)
    
    # Quellenangabe am Ende der Sidebar
    st.markdown("---")
    st.caption("""
    **Datenquellen:**
    - Distanzberechnung: OpenStreetMap via GeoPy
    - CO2-Faktoren: Durchschnittswerte basierend auf öffentlichen Umweltdatenbanken
    - ML-Modell: Trainiert auf synthetischen Daten (Demozwecke)
    """)

# CO2-Emissionsfaktoren für verschiedene Transportmittel
emission_factors = {
    "Auto": 0.17,      
    "Flugzeug": 0.24,  
    "Zug": 0.04,       
    "Bus": 0.07,       
    "Motorrad": 0.11   
}

# Distanzfaktoren für realistischere Routenberechnung
distance_factors = {
    "Auto": 1.2,       
    "Flugzeug": 1.0,   
    "Zug": 1.3,       
    "Bus": 1.3,      
    "Motorrad": 1.2    
}

# Hauptfunktion zur Berechnung des CO2-Fussabdrucks
def calculate_co2_footprint(start, end, transports, num_travelers):
    # Geocoding von Start- und Endpunkt
    geolocator = Nominatim(user_agent="co2_footprint_tracker", timeout=5)
    
    try:    # Versuche, Start- und Endadresse in Koordinaten umzuwandeln
        start_location = geolocator.geocode(start)
        end_location = geolocator.geocode(end)
        
        if not start_location or not end_location:  # Wenn einer der Orte nicht geunden wird, zeige Fehlermeldung im UI
            st.error("Konnte einen oder beide Standorte nicht finden. Bitte überprüfe deine Eingaben.")
            return None
        
        # Extrahiere Breite- und Längengrad für Distanzberechnung
        start_coords = (start_location.latitude, start_location.longitude)
        end_coords = (end_location.latitude, end_location.longitude)
        
        # Berechne die direkte Luftlinie in Kilometern (zweistellige Genauigkeit)
        direct_distance = round(geodesic(start_coords, end_coords).kilometers, 2)
        
        # Realistischere Distanzen für verschiedene Transportmittel (Anpassungsfaktoren)
        distance_factors = {
            "Auto": 1.2,
            "Flugzeug": 1.0,
            "Zug": 1.3,
            "Bus": 1.3,
            "Motorrad": 1.2,
        }
        
        # Berechnung der CO2-Emissionen für die ausgewählten Transportmittel
        results = []
        for transport in transports:
            # Gesamtstrecke = direkte Luftlinie × Faktor
            distance    = direct_distance * distance_factors[transport]
            # CO2-Ausstoss pro Kilometer (aus globaler Variable emission_factors)
            co2_per_km  = emission_factors[transport]
            # Gesamter CO2-Ausstoss (kg)
            total_co2   = distance * co2_per_km
            # Emission pro Person
            co2_per_person = total_co2 / num_travelers
            
            # Füge die berechneten Werte als Dictionary zur Liste hinzu
            results.append({
                "Transportmittel": transport,
                "Distanz (km)": round(distance, 2),
                "CO2 pro Person (kg)": round(co2_per_person, 2),
                "Gesamt CO2 (kg)": round(total_co2, 2)
            })
        
        # Gib ein DataFrame mit allen Ergebnissen plus Zusatzinfos zurück
        return pd.DataFrame(results), direct_distance, start_coords, end_coords
    
    except Exception as e:
        # Bei unerwarteten Fehlern im Try-Block: Fehlermeldung anzeigen
        st.error(f"Fehler bei der Berechnung: {e}")
        return None

# Hauptbereich - Ergebnisdarstellung
if calculate_button:
    with st.spinner("Berechne CO2-Fussabdruck..."): # Zeige während der Berechnung einen Lade-Indikator an
        result = calculate_co2_footprint(start_point, end_point, selected_transports, travelers)
        
        if result:  # Wenn die Funktion gültige Daten zurückliefert
            df, direct_distance, start_coords, end_coords = result
            
            # Ergebnisübersicht
            st.header(f"Reise von {start_point} nach {end_point}")
            st.write(f"Direkte Entfernung: {direct_distance} km")
            
            # Daten anzeigen
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # CO2-Vergleichsdiagramm
                fig = px.bar(
                    df,
                    x="Transportmittel",
                    y="CO2 pro Person (kg)",
                    color="Transportmittel",
                    title=f"CO2-Vergleich verschiedener Transportmittel für {travelers} Reisende",
                    labels={"CO2 pro Person (kg)": "CO2-Emissionen pro Person (kg)"}
                )
                fig.update_layout(height=500)   # Höhe des Diagramms anpassen
                st.plotly_chart(fig, use_container_width=True)
                
                # Umweltauswirkungen visualisieren
                st.subheader("Umweltauswirkungen")
                for transport in df["Transportmittel"]:
                    # Greife die Zeile zum jeweiligen Transportmittel ab
                    transport_data = df[df["Transportmittel"] == transport].iloc[0]
                    co2 = transport_data["CO2 pro Person (kg)"]
                    
                    # Umweltvergleich erstellen
                    trees_needed = round(co2 / 21, 2)  
                    equivalent_days = round(co2 / 10, 1)  
                    
                    # Ausgabe der Vergleiche
                    st.write(f"**{transport}:** {co2} kg CO2 pro Person")
                    st.write(f"Entspricht dem CO2, das {trees_needed} Bäume in einem Jahr aufnehmen")
                    st.write(f"Oder den durchschnittlichen CO2-Emissionen von {equivalent_days} Tagen")
                    st.write("---")
            
            with col2:
                # Detaillierte Ergebnistabelle
                st.subheader("Details")
                st.dataframe(df, use_container_width=True)
                
                # Tipps zur Reduzierung des CO2-Fussabdrucks
                st.subheader("Tipps zum CO2-Sparen")
                tips = [
                    "Wähle möglichst oft öffentliche Verkehrsmittel",
                    "Erwäge Fahrgemeinschaften für Autofahrten",
                    "Kompensiere deine CO2-Emissionen durch Klimaschutzprojekte",
                    "Vermeide Kurzstreckenflüge, wenn möglich",
                    "Kombiniere Reisen, um Wege zu sparen"
                ]
                for tip in tips:
                    st.write(f"- {tip}")
    
            # Vergleichende Darstellung
            st.header("CO2-Einsparpotential")
            # Nur anzeigen, wenn mehr als ein Transportmittel gewählt wurde
            if len(selected_transports) > 1:
                min_co2_transport = df.loc[df["CO2 pro Person (kg)"].idxmin()]["Transportmittel"]
                max_co2_transport = df.loc[df["CO2 pro Person (kg)"].idxmax()]["Transportmittel"]
                
                min_co2 = df[df["Transportmittel"] == min_co2_transport]["CO2 pro Person (kg)"].values[0]
                max_co2 = df[df["Transportmittel"] == max_co2_transport]["CO2 pro Person (kg)"].values[0]
                
                # Berechne die absolute und relative Ersparnis
                savings = max_co2 - min_co2
                saving_percentage = (savings / max_co2) * 100
                
                # Gib dem Nutzer einen klaren Vergleichstext aus
                st.write(f"Durch die Wahl von **{min_co2_transport}** statt **{max_co2_transport}** kannst du **{savings:.2f} kg CO2** pro Person einsparen.")
                st.write(f"Das entspricht einer Reduktion von **{saving_percentage:.1f}%**!")
                
                # Visualisierung des Einsparpotentials
                saving_data = pd.DataFrame([
                    {"Transport": max_co2_transport, "CO2 (kg)": max_co2, "Typ": "Höchste Emissionen"},
                    {"Transport": min_co2_transport, "CO2 (kg)": min_co2, "Typ": "Niedrigste Emissionen"}
                ])
                
                 # Zeichne Balkendiagramm, das die Differenz visuell hervorhebt
                fig = px.bar(
                    saving_data,
                    x="Transport",
                    y="CO2 (kg)",
                    color="Typ",
                    title="CO2-Einsparpotential durch Wahl des umweltfreundlichsten Transportmittels",
                    color_discrete_map={"Höchste Emissionen": "red", "Niedrigste Emissionen": "green"}
                )
                st.plotly_chart(fig, use_container_width=True)
                
            # Machine Learning Ergebnisse, wenn aktiviert
            if use_ml and "Auto" in selected_transports:
                st.header("Machine Learning Analyse für Autofahrten")
                
                # Auto-Distanz extrahieren
                auto_distance = df[df["Transportmittel"] == "Auto"]["Distanz (km)"].values[0]
                
                # Standard-CO2-Berechnung
                standard_co2 = df[df["Transportmittel"] == "Auto"]["CO2 pro Person (kg)"].values[0]
                
                # ML-Vorhersage
                ml_co2 = predict_co2_with_ml(
                    auto_distance,
                    vehicle_age,
                    vehicle_type,
                    season,
                    traffic_level,
                    model,
                    feature_columns
                )
                ml_co2_per_person = ml_co2 / travelers
                
                # Vergleich anzeigen
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Vergleich der CO2-Berechnungen")
                     # Ausgabe der Standard- und ML-Berechnung als Text
                    st.write(f"**Standard-Berechnung:** {standard_co2:.2f} kg CO2 pro Person")
                    st.write(f"**ML-Berechnung:** {ml_co2_per_person:.2f} kg CO2 pro Person")
                    
                    # Differenz und Prozentualer Unterschied
                    difference = ml_co2_per_person - standard_co2
                    percentage = (difference / standard_co2) * 100
                    
                    # Unterschiedstext je nach Richtung der Abweichung
                    if difference > 0:
                        st.write(f"Das ML-Modell schätzt **{abs(difference):.2f} kg ({abs(percentage):.1f}%)** mehr CO2-Emissionen als die Standardberechnung.")
                    else:
                        st.write(f"Das ML-Modell schätzt **{abs(difference):.2f} kg ({abs(percentage):.1f}%)** weniger CO2-Emissionen als die Standardberechnung.")
                    
                    # Einflussfaktoren erklären
                    st.write(f"""
                    **Einflussfaktoren auf die ML-Vorhersage:**
                    - Fahrzeugtyp: {vehicle_type} ({"erhöht" if vehicle_type in ["SUV", "Luxusklasse"] else "reduziert"} CO2-Emissionen)
                    - Fahrzeugalter: {vehicle_age} Jahre ({"erhöht" if vehicle_age > 5 else "neutral für"} CO2-Emissionen)
                    - Jahreszeit: {season} ({"erhöht" if season in ["Winter", "Herbst"] else "reduziert"} CO2-Emissionen)
                    - Verkehrsaufkommen: {traffic_level}/10 ({"erhöht" if traffic_level > 5 else "neutral für"} CO2-Emissionen)
                    """)
                
                with col2:
                    # Vergleichsdiagramm
                    compare_df = pd.DataFrame([
                        {"Methode": "Standard-Berechnung", "CO2 (kg)": standard_co2},
                        {"Methode": "ML-Berechnung", "CO2 (kg)": ml_co2_per_person}
                    ])
                    
                    fig = px.bar(
                        compare_df,
                        x="Methode",
                        y="CO2 (kg)",
                        color="Methode",
                        title="Vergleich der CO2-Berechnungsmethoden",
                        labels={"CO2 (kg)": "CO2-Emissionen pro Person (kg)"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Feature Importance aus dem Random Forest extrahieren und visualisieren
                st.subheader("Feature Importance: Welche Faktoren beeinflussen die CO2-Emissionen?")
                
                # Feature Importance berechnen
                feature_importance = pd.DataFrame({
                    'Feature': feature_columns,
                    'Importance': model.feature_importances_
                }).sort_values('Importance', ascending=False)
                
                # Visualisieren
                fig = px.bar(
                    feature_importance.head(10),
                    x='Importance',
                    y='Feature',
                    orientation='h',
                    title='Top 10 Einflussfaktoren auf CO2-Emissionen',
                    color='Importance',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Modellbeschreibung
                st.subheader("Über das ML-Modell")
                st.write("""
                Das Machine Learning-Modell verwendet einen Random Forest-Algorithmus, um CO2-Emissionen basierend auf verschiedenen Faktoren vorherzusagen. 
                Im Gegensatz zur Standard-Berechnung, die nur Distanz und Transportmittel berücksichtigt, kann das ML-Modell komplexere Zusammenhänge erfassen.
                
                **Berücksichtigte Faktoren:**
                - Fahrzeugtyp (Kleinwagen, Mittelklasse, SUV, Luxusklasse)
                - Fahrzeugalter (beeinflusst Treibstoffeffizienz)
                - Jahreszeit (beeinflusst Heizung/Klimaanlage)
                - Verkehrsaufkommen (beeinflusst Staus und Stop-and-Go-Verkehr)
                - Distanz (Grundlage der Berechnung)
                
                In einer realen Anwendung könnte das Modell mit echten Daten trainiert werden, um noch genauere Vorhersagen zu treffen.
                """)
            elif use_ml and "Auto" not in selected_transports:
                st.warning("Die ML-Analyse ist nur für Autofahrten verfügbar. Bitte wähle 'Auto' als Transportmittel aus.")

# Abschnitt für zukünftige Erweiterungen
st.markdown("---")
st.subheader("Unterstützte Transportmittel")
col1, col2, col3 = st.columns(3)

with col1:
    st.write("🚗 Auto")
    st.write("✈️ Flugzeug")
with col2:
    st.write("🚂 Zug")
    st.write("🚌 Bus")
with col3:
    st.write("🏍️ Motorrad")

# Über die App
st.markdown("---")
st.subheader("Über die App")
st.write("""
Diese App wurde im Rahmen eines Gruppenprojekts für den Kurs 'Grundlagen und Methoden der Informatik' 
an der Universität St. Gallen entwickelt. Sie hilft Nutzern, den ökologischen Fussabdruck ihrer Reisen 
zu verstehen und umweltbewusstere Entscheidungen zu treffen.

Die App integriert sowohl konventionelle Berechnungsmethoden als auch fortschrittliche 
Machine Learning-Techniken, um präzisere CO2-Vorhersagen zu ermöglichen.
""")



# Sources:
# 	• Streamlit-Dokumentation: Die Benutzeroberfläche wurde mithilfe des Streamlit-Frameworks erstellt: https://docs.streamlit.io/library/get-started
# 	• Geopy-Bibliothek: Für die Geocodierung und Distanzberechnung wurde die Geopy-Bibliothek verwendet: https://geopy.readthedocs.io/en/stable/
# 	• Plotly Express: Die interaktiven Visualisierungen wurden mit Plotly Express erstellt: https://plotly.com/python/plotly-express/
# 	• Scikit-learn: Das Machine Learning-Modell wurde mit Scikit-learn implementiert: https://scikit-learn.org/stable/modules/ensemble.html#forest
# 	• CO2-Emissionsdaten: Die verwendeten Emissionsfaktoren basieren auf Durchschnittswerten aus öffentlichen Forschungsdaten des Umweltbundesamtes: https://www.umweltbundesamt.de/themen/verkehr-laerm/emissionsdaten
# 	• OpenStreetMap: Die geografischen Daten für die Routenberechnung stammen von OpenStreetMap via Geopy: https://www.openstreetmap.org/
# 	• Umweltauswirkungen: Die Umrechnung in Baum-Äquivalente basiert auf wissenschaftlichen Studien zur CO2-Bindung durch Bäume: https://www.forstwirtschaft-in-deutschland.de/waelder-entdecken/waldfunktionen/klimaschutz/
# 	• ChatGPT und GitHub Copilot: Verwendet für Code-Optimierung und Debugging
