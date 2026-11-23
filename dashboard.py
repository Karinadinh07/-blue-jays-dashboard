import streamlit as st
import pandas as pd

# Set up the dashboard
st.set_page_config(page_title="Blue Jays Pitch Analysis", page_icon="⚾", layout="wide")

DATA_FILE = "Data_MLB_2025_StatcastPostseason_PitchByPitch_20251102a.csv"
WHIFF_EVENTS = ["swinging_strike", "swinging_strike_blocked"]
CONTACT_EVENTS = ["foul", "foul_tip", "hit_into_play", "foul_bunt"]

# Load the postseason data
try:
    df = pd.read_csv(DATA_FILE)
except FileNotFoundError:
    st.error(f"CSV file not found: {DATA_FILE}. Put the CSV next to dashboard.py.")
    st.stop()

needed = ["home_team", "away_team", "inning_topbot", "player_name", "pitch_name", "description", "plate_x", "plate_z", "balls", "strikes"]
missing = [column for column in needed if column not in df.columns]
if missing:
    st.error("Missing columns in CSV: " + ", ".join(missing))
    st.stop()

# Keep pitches thrown by Toronto pitchers (when Toronto is fielding)
blue_jays = df[
    ((df["home_team"] == "TOR") & (df["inning_topbot"] == "Top")) |
    ((df["away_team"] == "TOR") & (df["inning_topbot"] == "Bot"))
].copy()

if blue_jays.empty:
    st.warning("No Toronto pitching records were found in this file.")
    st.stop()

# Mark swings and misses using the same event lists throughout
blue_jays["is_whiff"] = blue_jays["description"].isin(WHIFF_EVENTS)
blue_jays["is_contact"] = blue_jays["description"].isin(CONTACT_EVENTS)
blue_jays["is_swing"] = blue_jays["is_whiff"] | blue_jays["is_contact"]

# Calculate whiff rate for each group
# Whiff rate = missed swings / recorded swings * 100
def whiff_summary(data, group_column):
    swings = data[data["is_swing"]]
    if swings.empty:
        return pd.DataFrame(columns=["Whiff Rate (%)", "Swings", "Whiffs"])
    result = swings.groupby(group_column).agg(
        Swings=("is_swing", "size"),
        Whiffs=("is_whiff", "sum")
    )
    result["Whiff Rate (%)"] = result["Whiffs"] / result["Swings"] * 100
    return result.sort_values("Whiff Rate (%)", ascending=False)

# Title and project explanation
st.title("⚾ Toronto Blue Jays 2025 Postseason Pitch Analysis")
st.write("Explore pitch types, whiff rates, pitch locations, and pitcher performance during the 2025 MLB postseason.")

with st.expander("About This Project & Baseball Terms", expanded=True):
    st.write(
        "This project studies which pitch types and locations generated swings and misses "
        "for Toronto Blue Jays pitchers, and how patterns varied by pitcher and ball-strike count."
    )
    st.info(
        "**Pitcher:** throws the ball.  **Batter:** tries to hit the ball.  "
        "**Pitch type:** kind of pitch, such as a slider or fastball.  "
        "**Whiff:** a swing that misses.  **Whiff rate:** missed swings divided by recorded swings."
    )

# Filters stay together in the sidebar
st.sidebar.header("⚾ Explore the Data")
pitch_options = sorted(blue_jays["pitch_name"].dropna().unique())
pitcher_options = sorted(blue_jays["player_name"].dropna().unique())
if not pitch_options or not pitcher_options:
    st.error("No pitch types or pitcher names are available.")
    st.stop()

selected_pitch = st.sidebar.selectbox("Select a Pitch Type", pitch_options)
selected_pitcher = st.sidebar.selectbox("Select a Pitcher", pitcher_options)
st.sidebar.caption("The selected pitcher and pitch type control the detailed analysis. Comparison charts use the relevant selection only.")

# Filter data for the chosen pitcher and pitch type
pitch_type_data = blue_jays[blue_jays["pitch_name"] == selected_pitch]
pitcher_data = blue_jays[
    (blue_jays["pitch_name"] == selected_pitch) &
    (blue_jays["player_name"] == selected_pitcher)
]
selected_swings = pitcher_data[pitcher_data["is_swing"]]
whiffs = pitcher_data[pitcher_data["is_whiff"]]
contact = pitcher_data[pitcher_data["is_contact"]]
total_swings = len(selected_swings)
whiff_rate = len(whiffs) / total_swings * 100 if total_swings else None

# Four tabs organize the dashboard
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Overview", "⚾ Pitch Analysis", "📍 Locations", "🔢 Counts"
])

with tab1:
    st.header("Overview")
    a, b, c = st.columns(3)
    a.metric("Total Blue Jays Pitches", f"{len(blue_jays):,}")
    b.metric("Total Pitchers", blue_jays["player_name"].nunique())
    c.metric("Pitch Types", blue_jays["pitch_name"].nunique())

    st.subheader("Pitch Types Used by Blue Jays")
    st.caption("This chart shows how many pitches of each type Toronto pitchers threw.")
    pitch_counts = blue_jays["pitch_name"].value_counts()
    st.bar_chart(pitch_counts)
    with st.expander("View Pitch Type Counts"):
        st.dataframe(pitch_counts.rename("Pitches"), use_container_width=True)

with tab2:
    st.header("Pitch Analysis")
    st.caption("Use the sidebar to select a pitch type and a pitcher.")
    st.subheader("Selected Pitcher and Pitch Type")
    st.write(f"**Pitcher:** {selected_pitcher}  |  **Pitch Type:** {selected_pitch}")
    a, b, c = st.columns(3)
    a.metric("Total Pitches", len(pitcher_data))
    b.metric("Missed Swings", len(whiffs))
    c.metric("Whiff Rate", f"{whiff_rate:.2f}%" if whiff_rate is not None else "N/A")
    st.caption("Whiff rate counts missed swings out of recorded swings, not out of all pitches.")
    if total_swings == 0:
        st.info("No recorded swings for this pitcher and pitch type. Choose another combination.")
    else:
        # Show a single bar for the selected combination
        chart_data = pd.DataFrame({"Whiff Rate (%)": [whiff_rate]}, index=[selected_pitch])
        st.bar_chart(chart_data, y="Whiff Rate (%)")

    # Compare pitch types for the chosen pitcher
    st.subheader("Whiff Rate by Pitch Type")
    st.caption("Compare pitch types for the selected pitcher. A higher percentage means more missed swings among recorded swings.")
    all_pitcher_data = blue_jays[blue_jays["player_name"] == selected_pitcher]
    pitch_rates = whiff_summary(all_pitcher_data, "pitch_name")
    if pitch_rates.empty:
        st.info("No swing data available for this pitcher.")
    else:
        st.bar_chart(pitch_rates["Whiff Rate (%)"], y_label="Whiff Rate (%)")
        with st.expander("View Swing Counts by Pitch Type"):
            st.dataframe(pitch_rates, use_container_width=True)

    # Compare pitchers using the chosen pitch type
    st.subheader("Whiff Rate Comparison by Pitcher")
    st.caption("Compare pitchers using the selected pitch type. Check the number of swings before interpreting high percentages.")
    pitcher_rates = whiff_summary(pitch_type_data, "player_name")
    if pitcher_rates.empty:
        st.info("No swing data available for this pitch type.")
    else:
        st.bar_chart(pitcher_rates["Whiff Rate (%)"], y_label="Whiff Rate (%)")
        with st.expander("View Swing Counts by Pitcher"):
            st.dataframe(pitcher_rates, use_container_width=True)

    with st.expander("View Detailed Pitch Data"):
        st.dataframe(pitcher_data, use_container_width=True)

with tab3:
    st.header("Pitch Locations")
    st.write(f"Showing **{selected_pitch}** thrown by **{selected_pitcher}**.")
    st.subheader("All Pitch Locations")
    st.caption("Each dot shows where a selected pitch crossed home plate. Horizontal = plate_x; height = plate_z.")
    location_data = pitcher_data[["plate_x", "plate_z"]].dropna()
    if location_data.empty:
        st.info("No location data for this selection.")
    else:
        st.scatter_chart(location_data, x="plate_x", y="plate_z")

    st.subheader("Whiff Locations")
    st.caption("Each dot shows a pitch that caused a missed swing. This shows locations, not whiff rate by zone.")
    whiff_locations = whiffs[["plate_x", "plate_z"]].dropna()
    if whiff_locations.empty:
        st.info("No missed-swing locations for this selection.")
    else:
        st.scatter_chart(whiff_locations, x="plate_x", y="plate_z")

with tab4:
    st.header("Ball–Strike Count Analysis")
    st.caption("A count like 0-2 means zero balls and two strikes before the pitch.")
    count_data = selected_swings.copy()
    if count_data.empty:
        st.info("No recorded swings for this pitcher and pitch type.")
    else:
        count_data["count"] = (
            count_data["balls"].astype(str) + "-" + count_data["strikes"].astype(str)
        )
        count_rates = whiff_summary(count_data, "count")
        st.subheader("Whiff Rate by Ball–Strike Count")
        st.caption("Compare the percentage of missed swings at different counts for the selected pitcher and pitch type.")
        st.bar_chart(count_rates["Whiff Rate (%)"], y_label="Whiff Rate (%)")
        with st.expander("View Swing Counts by Count"):
            st.dataframe(count_rates, use_container_width=True)
            
st.divider()
st.caption(
    "Source: MLB 2025 postseason Statcast pitch-by-pitch CSV. "
    "Whiffs are swinging_strike and swinging_strike_blocked. "
    "Contact includes foul, foul_tip, hit_into_play, and foul_bunt. "
    "Confirm these event definitions match the group's notebook before submitting."
)
