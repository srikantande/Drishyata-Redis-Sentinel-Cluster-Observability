## GNU Affero General Public License v3.0 (AGPL-3.0)
# Copyright 2024-2025 Drishyata
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
#
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import streamlit as st
import redis
import time
import sqlite3
import pandas as pd
import math
import configparser

# --- 1. CONFIGURATION LOADING (Externalised) ---

CONFIG_FILE = "/opt/Drishyata/config.ini"

def load_config():
    """Loads configuration from the external config.ini file."""
    config = configparser.ConfigParser()
    try:
        if not config.read(CONFIG_FILE):
            st.error(f"Configuration file '{CONFIG_FILE}' not found or empty. Using defaults.")
            return {
                'sentinels': [('127.0.0.1', 26379)],
                'refresh_seconds': 60,
                'db_file': "redis_health_history.db"
            }

        sentinels_str = config.get('OBSERVABILITY', 'SENTINELS', fallback='127.0.0.1:26379')
        sentinel_list = []
        for entry in sentinels_str.split(','):
            try:
                host, port = entry.strip().split(':')
                sentinel_list.append((host, int(port)))
            except ValueError:
                continue

        return {
            'sentinels': sentinel_list,
            'refresh_seconds': config.getint('OBSERVABILITY', 'REFRESH_INTERVAL_SECONDS', fallback=60),
            'db_file': config.get('OBSERVABILITY', 'DB_FILE', fallback='redis_health_history.db')
        }
    except Exception as e:
        st.error(f"Error loading configuration from {CONFIG_FILE}: {e}")
        return {}

APP_CONFIG = load_config()
SENTINELS = APP_CONFIG.get('sentinels', [('127.0.0.1', 26379)])
REFRESH_INTERVAL_SECONDS = APP_CONFIG.get('refresh_seconds', 60)
DB_FILE = APP_CONFIG.get('db_file', "redis_health_history.db")

# --- Database Functions ---

def init_db():
    """Initializes the SQLite database and creates the tables if they don't exist."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cluster_name TEXT,
                role TEXT,
                host TEXT,
                port INTEGER,
                health TEXT,
                keys INTEGER,
                clients INTEGER,
                memory TEXT,
                master_host TEXT,
                master_port INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentinel_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                host TEXT,
                port INTEGER,
                masters_monitored INTEGER,
                is_tilt INTEGER,
                running_scripts INTEGER,
                total_clusters_monitored INTEGER
            )
        """)
        conn.commit()
    except Exception as e:
        st.error(f"Failed to initialize database: {e}")
    finally:
        if conn:
            conn.close()

def save_health_data(cluster_name, master_node, node_infos):
    """Saves the collected Redis node health data to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        master_host, master_port = master_node
        for info in node_infos:
            try:
                keys = info.get('Keys') if info.get('Keys') != 'n/a' else None
                clients = info.get('Clients') if info.get('Clients') != 'n/a' else None
                cursor.execute("""
                    INSERT INTO health_snapshots (timestamp, cluster_name, role, host, port, health, keys, clients, memory, master_host, master_port)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    current_time, cluster_name, info['Role'], info['Host'], info['Port'], info['Health'],
                    keys, clients, info['Memory'], master_host, master_port
                ))
            except Exception:
                pass
        conn.commit()
    except Exception as e:
        st.error(f"Failed to save data batch to database: {e}")
    finally:
        if conn:
            conn.close()

def save_sentinel_data(sentinel_infos):
    """Saves the collected sentinel health data to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        for info in sentinel_infos:
            cursor.execute("""
                INSERT INTO sentinel_snapshots (
                    timestamp, host, port, masters_monitored, is_tilt, running_scripts, total_clusters_monitored
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                current_time, info['Host'], info['Port'], info['masters_monitored'],
                info['is_tilt'], info['running_scripts'], info['masters_monitored']
            ))
        conn.commit()
    except Exception as e:
        st.error(f"Failed to save sentinel data batch to database: {e}")
    finally:
        if conn:
            conn.close()

def get_redis_history_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT timestamp, cluster_name, role, host, port, health, keys, clients, memory, master_host, master_port FROM health_snapshots ORDER BY timestamp DESC", conn)
    conn.close()
    return df

def get_sentinel_history_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT id, timestamp, host, port, masters_monitored, is_tilt, running_scripts FROM sentinel_snapshots ORDER BY timestamp DESC", conn)
    conn.close()
    return df

# --- Helper: Direct Sentinel Connection ---

def get_sentinel_connection():
    """Tries to connect to the first available Sentinel and returns the connection object."""
    for host, port in SENTINELS:
        try:
            r = redis.StrictRedis(host=host, port=port, decode_responses=True, socket_timeout=2)
            if r.ping():
                return r
        except Exception:
            continue
    return None

# --- UI/UX & Observability Helpers ---

def format_health_metric(label, value, is_critical=False):
    """Helper to display key metrics using Streamlit metric/markdown for eye-catchy observability."""
    icon = "✅" if value == 'Healthy' else ("❌" if value in ['Down/Error', 'Unhealthy', 'Error'] else "⚠️" if is_critical or value == 'Discovery Error' else "📊")
    color = "green" if value == 'Healthy' else ("red" if value in ['Down/Error', 'Unhealthy', 'Error', 'Discovery Error'] else ("orange" if is_critical else "grey"))

    st.markdown(f"""
        <div style='
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 5px solid {color};
            background-color: #f0f2f6;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        '>
            <small style='color: #6c757d;'>{label}</small><br>
            <strong style='font-size: 1.2em; color: black;'>{icon} {value}</strong>
        </div>
    """, unsafe_allow_html=True)

# Function for Styler.map
def style_health_status(val):
    if val in ['Down/Error', 'Unhealthy', 'Error']:
        return 'background-color: #f7d7d7'  # Reddish for errors
    elif val == 'Healthy':
        return 'background-color: #d7f7d7' # Greenish for healthy
    return ''

# --- View Functions ---

def live_monitor_view(placeholder):
    """Fetches and displays Redis health data with enhanced UI/UX."""

    with placeholder.container():
        # --- HEADING CHANGE ---
        st.header("💾 Live Redis Cluster Observability")
        # ----------------------

        sentinel_conn = get_sentinel_connection()

        if not sentinel_conn:
            st.error("❌ Critical: Could not connect to ANY configured Sentinel nodes.")
            return

        monitored_masters = {}
        try:
            monitored_masters = sentinel_conn.sentinel_masters()
        except Exception as e:
            st.error(f"Error fetching masters list: {e}")
            return

        if not monitored_masters:
            st.warning("⚠️ Sentinel is reachable, but is not monitoring any masters.")
            return

        sentinel_infos = []

        # Iterate through every discovered cluster
        for master_name, master_data in monitored_masters.items():

            master_ip = master_data.get('ip')
            master_port = master_data.get('port')
            master_status = 'N/A'
            slave_count = 0
            keys_count = 0
            total_memory = 'N/A'
            node_infos = []

            if master_ip and master_port:
                master_node = (master_ip, master_port)
                slaves = []
                try:
                    slaves_data = sentinel_conn.sentinel_slaves(master_name)
                    slave_count = len(slaves_data)
                    for slave in slaves_data:
                        slaves.append((slave.get('ip'), slave.get('port')))

                    all_nodes = [(master_ip, master_port, 'Master')] + [(h, p, 'Slave') for h, p in slaves]

                    # Gather detailed info for all nodes
                    for host, port, role in all_nodes:
                        try:
                            r = redis.StrictRedis(host=host, port=port, decode_responses=True, socket_timeout=1)
                            info = r.info()
                            dbsize = r.dbsize()
                            clients = info.get('connected_clients', 'n/a')
                            mem = info.get('used_memory_human', 'n/a')
                            status = 'Healthy' if r.ping() else 'Unhealthy'

                            node_info = {
                                'Role': role, 'Host': host, 'Port': port, 'Health': status,
                                'Keys': dbsize, 'Clients': clients, 'Memory': mem,
                            }
                            node_infos.append(node_info)

                            if role == 'Master':
                                master_status = status
                                keys_count = dbsize
                                total_memory = mem

                        except Exception:
                            node_infos.append({
                                'Role': role, 'Host': host, 'Port': port,
                                'Health': 'Down/Error', 'Keys': 'n/a', 'Clients': 'n/a', 'Memory': 'n/a',
                            })
                            if role == 'Master':
                                master_status = 'Down/Error'

                except Exception:
                    master_status = 'Discovery Error'

                save_health_data(master_name, master_node, node_infos)

                # --- START: CLUSTER VISIBLE DETAILS ---

                st.subheader(f"Cluster: **{master_name}**")

                # OBSERVABILITY: Use metric style for key parameters (ALWAYS VISIBLE)
                col1, col2, col3, col4 = st.columns(4)
                with col1: format_health_metric("Master Health", master_status, is_critical=master_status != 'Healthy')
                with col2: format_health_metric("Keys (Master)", f"{keys_count:,}" if isinstance(keys_count, int) else str(keys_count), is_critical=False)
                with col3: format_health_metric("Used Memory (Master)", total_memory, is_critical=False)
                with col4: format_health_metric("Slaves Count", slave_count, is_critical=slave_count < 1)

                # --- START: NODE DETAILS EXPANDER (NEW) ---
                with st.expander("Show Node Details Table"):
                    # Display the Node Details Table (NOW INSIDE EXPANDER)
                    st.dataframe(
                        pd.DataFrame(node_infos).style.map(style_health_status, subset=['Health']),
                        hide_index=True,
                        width='stretch',
                        column_order=['Role', 'Host', 'Port', 'Health', 'Keys', 'Clients', 'Memory'] # Ensure order
                    )
                # --- END: NODE DETAILS EXPANDER ---

                st.markdown("---") # Separator between clusters

                # --- END: CLUSTER VISIBLE DETAILS ---


        # -------------------------------------
        # Global Sentinel Status
        # -------------------------------------
        st.subheader("🛡️ Sentinel Network Health")

        for host, port in SENTINELS:
            try:
                rs = redis.StrictRedis(host=host, port=port, decode_responses=True, socket_timeout=1)
                s_info = rs.info('sentinel')
                status = 'Healthy' if rs.ping() else 'Unhealthy'

                info_row = {
                    'Host': host, 'Port': port, 'Status': status,
                    'masters_monitored': s_info.get('sentinel_masters', 0),
                    'is_tilt': s_info.get('sentinel_tilt', 0),
                    'running_scripts': s_info.get('sentinel_running_scripts', 0),
                }
                sentinel_infos.append(info_row)

            except Exception:
                sentinel_infos.append({
                    'Host': host, 'Port': port, 'Status': 'Error',
                    'masters_monitored': 0, 'is_tilt': 1, 'running_scripts': 0
                })

        if sentinel_infos:
            save_sentinel_data(sentinel_infos)
            sentinel_df = pd.DataFrame(sentinel_infos)

            col1_s, col2_s, col3_s = st.columns(3)
            healthy_sentinels = len(sentinel_df[sentinel_df['Status'] == 'Healthy'])
            tilt_count = sentinel_df['is_tilt'].sum()

            with col1_s: format_health_metric("Active Sentinels", f"{healthy_sentinels}/{len(SENTINELS)}", is_critical=healthy_sentinels == 0)
            with col2_s: format_health_metric("Total Masters Monitored", sentinel_df['masters_monitored'].max(), is_critical=False)
            with col3_s: format_health_metric("Tilt/Script Issues", tilt_count, is_critical=tilt_count > 0)

            with st.expander("Sentinel Detail Table"):
                st.dataframe(
                    sentinel_df.style.map(style_health_status, subset=['Status']),
                    hide_index=True,
                    width='stretch'
                )


        st.markdown("---")
        st.caption(f"Last updated: **{time.strftime('%Y-%m-%d %H:%M:%S')}** | Auto-refresh: **{REFRESH_INTERVAL_SECONDS}s**")

def display_history_view(placeholder):
    """Displays history with improved UI for large datasets."""
    with placeholder.container():
        st.header("⏳ Historical Status Snapshots")
        PAGE_SIZE = 5000

        tab1, tab2 = st.tabs(["Redis Node History", "Sentinel Node History"])

        with tab1:
            st.subheader("Redis Cluster Node History")
            history_df = get_redis_history_data()

            if history_df.empty:
                st.info("No historical Redis Node data found.")
            else:
                col_filt, col_info = st.columns([1, 4])

                with col_filt:
                    unique_clusters = history_df['cluster_name'].unique()
                    selected_cluster = st.selectbox("Filter by Cluster Name", options=['All'] + list(unique_clusters), key="redis_cluster_filter")

                if selected_cluster != 'All':
                    history_df = history_df[history_df['cluster_name'] == selected_cluster]

                total_records = len(history_df)
                total_pages = math.ceil(total_records / PAGE_SIZE)

                with col_info:
                    st.metric("Total Filtered Records", f"{total_records:,}")

                col_select, col_download = st.columns([1, 4])
                with col_select:
                    selected_page = st.selectbox("Select Page", options=range(1, total_pages + 1), index=0, key="redis_page_select") if total_pages > 0 else 1

                start_index = (selected_page - 1) * PAGE_SIZE
                end_index = start_index + PAGE_SIZE
                page_df = history_df.iloc[start_index:end_index]

                st.dataframe(
                    page_df,
                    width='stretch',
                    column_order=['timestamp', 'cluster_name', 'host', 'port', 'role', 'health', 'keys', 'clients', 'memory'],
                    hide_index=True
                )

                with col_download:
                    st.download_button(
                        label="⬇️ Download Full History CSV",
                        data=history_df.to_csv(index=False).encode('utf-8'),
                        file_name=f'redis_history_{time.strftime("%Y%m%d")}.csv',
                        mime='text/csv',
                    )

        with tab2:
            st.subheader("Sentinel Node History")
            history_df = get_sentinel_history_data()

            if history_df.empty:
                 st.info("No historical Sentinel Node data found.")
            else:
                st.dataframe(
                    history_df,
                    hide_index=True,
                    width='stretch'
                )
                st.download_button(
                    label="⬇️ Download Sentinel History CSV",
                    data=history_df.to_csv(index=False).encode('utf-8'),
                    file_name=f'sentinel_history_{time.strftime("%Y%m%d")}.csv',
                    mime='text/csv',
                )

# --- Main Application Flow ---

st.set_page_config(page_title="Redis Sentinel Cluster Monitor", layout="wide", initial_sidebar_state="expanded")

# --- Branding ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    try:
        # Assuming you have a logo.png, otherwise this will fall back to the text
        st.image("/opt/Drishyata/logo.png", width=130)
    except Exception:
        st.markdown("## ⚙️")

with col_title:
    st.title('Multi-Cluster Redis Monitor')
    st.markdown("A unified observability tool for Redis Sentinel environments.")

# --- Sidebar & Navigation ---
st.sidebar.title("App Controls")
view_selection = st.sidebar.radio("Select View", ('Live Monitor', 'History Viewer'), index=0)

st.sidebar.markdown("---")
st.sidebar.caption("© Drishyata 2025. All rights reserved.")
st.sidebar.caption("Srikant Ande (Srikant.Ande<at>gmail.com)")
st.sidebar.markdown("---")
st.sidebar.caption("**Licensed under AGPL v3.0.**")

# Initialize DB on first load
if 'db_init' not in st.session_state:
    init_db()
    st.session_state['db_init'] = True

# Main content placeholder
main_placeholder = st.empty()

if view_selection == 'Live Monitor':
    live_monitor_view(main_placeholder)

    if REFRESH_INTERVAL_SECONDS > 0:
        time.sleep(REFRESH_INTERVAL_SECONDS)
        st.rerun()
else:
    display_history_view(main_placeholder)
