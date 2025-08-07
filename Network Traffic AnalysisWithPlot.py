import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import socket
import requests
import time

# Set page config to wide layout to utilize blank space
st.set_page_config(layout="wide")

# Custom CSS for yellow and black theme
st.markdown("""
    <style>
    .stApp {
        background-color: #000000;
        color: #FFD700;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #FFD700;
    }
    .stButton > button {
        background-color: #FFD700;
        color: #000000;
        border: none;
        border-radius: 4px;
    }
    .stButton > button:hover {
        background-color: #DAA520;
        color: #000000;
    }
    .stDateInput > div > div > input,
    .stSelectbox > div > div > div > input {
        background-color: #333333;
        color: #FFD700;
        border: 1px solid #FFD700;
    }
    section[data-testid="stSidebar"] {
        background-color: #111111;
    }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stButton > button {
        color: #FFD700;
    }
    .js-plotly-plot .plotly .modebar {
        background-color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = datetime.today()
if 'dst_counts_frame1' not in st.session_state:
    st.session_state.dst_counts_frame1 = None
if 'dst_counts_frame2' not in st.session_state:
    st.session_state.dst_counts_frame2 = None
if 'full_dst_counts' not in st.session_state:
    st.session_state.full_dst_counts = None
if 'unique_ips' not in st.session_state:
    st.session_state.unique_ips = []
if 'unique_dstports' not in st.session_state:
    st.session_state.unique_dstports = []

# Database and API functions (unchanged)
def get_domain_name(ip_address):
    try:
        hostname = socket.gethostbyaddr(ip_address)[0]
        return hostname
    except (socket.herror, OSError):
        return ip_address

def insert_ip_info(ip_address, count, domain):
    start_time = time.time()
    try:
        url = f"https://api.ipinfo.io/lite/{ip_address}?token=cf9348bd3ea2ab"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        ip = data.get('ip', 'N/A')
        asn = data.get('asn', 'N/A')
        as_name = data.get('as_name', 'N/A')
        as_domain = data.get('as_domain', 'N/A')
        country_code = data.get('country_code', 'N/A')
        country = data.get('country', 'N/A')
        continent_code = data.get('continent_code', 'N/A')
        continent = data.get('continent', 'N/A')
        unique_id = int(time.time() * 1000000)
        if not domain or domain == ip_address:
            domain = as_domain if as_domain and as_domain != 'N/A' else get_domain_name(ip_address)
        try:
            with mysql.connector.connect(
                host="192.168.100.25",
                user="sysuser",
                password="DT1Y9Q0EtBwI0",
                database="syslog"
            ) as engine:
                cursor = engine.cursor()
                cursor.execute("SELECT ip FROM LOG_DNS WHERE ip = %s", (ip,))
                if cursor.fetchone() is None:
                    insert_query = """
                        INSERT INTO LOG_DNS (ID, ip, asn, NAME, DOMAIN, country_code, country, continent_code, continent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (unique_id, ip, asn, as_name, domain, country_code, country, continent_code, continent))
                    engine.commit()
        except mysql.connector.Error as e:
            st.error(f"Error inserting IP info for {ip_address} into LOG_DNS: {e}")
        return {'domain': domain, 'data': data}
    except requests.RequestException as e:
        st.error(f"Error fetching IP info for {ip_address}: {e}")
        return {'domain': ip_address, 'data': None}

def check_plot_data(date_str, log_type, port=None):
    try:
        with mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        ) as engine:
            cursor = engine.cursor()
            log_id = f"log_{date_str}"
            if log_type == "PORT":
                query = "SELECT PORT, COUNT FROM PLOT_DATA WHERE LOG_ID = %s AND LOG_TYPE = %s"
                cursor.execute(query, (log_id, "PORT"))
                results = cursor.fetchall()
                if results:
                    df = pd.DataFrame(results, columns=['dstport', 'count'])
                    df['count'] = pd.to_numeric(df['count'], errors='coerce')
                    return df
                return None
            elif log_type == "DOMAIN" and port:
                query = "SELECT DOMAIN, COUNT FROM PLOT_DATA WHERE LOG_ID = %s AND LOG_TYPE = %s AND PORT = %s"
                cursor.execute(query, (log_id, "DOMAIN", port))
                results = cursor.fetchall()
                if results:
                    df = pd.DataFrame(results, columns=['domain', 'count'])
                    df['count'] = pd.to_numeric(df['count'], errors='coerce')
                    return df
                return None
    except mysql.connector.Error as e:
        st.error(f"Error checking PLOT_DATA for {date_str}: {e}")
        return None

def fetch_data_frame1(date_str):
    try:
        with mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        ) as engine:
            query = f"SELECT dst, dstport, COUNT(*) as count FROM log_{date_str} GROUP BY dst, dstport"
            df = pd.read_sql(query, engine)
            if not df.empty:
                df['count'] = pd.to_numeric(df['count'], errors='coerce')
            return df
    except mysql.connector.Error as e:
        st.error(f"Error fetching data for frame1: {e}")
        return None

def fetch_data_frame2(date_str):
    try:
        with mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        ) as engine:
            query = f"""
                SELECT dstport, dst, COUNT(*) as count
                FROM log_{date_str}
                WHERE dstport != '0'
                GROUP BY dstport, dst
                ORDER BY dstport, count DESC
            """
            df = pd.read_sql(query, engine)
            if not df.empty:
                df['count'] = pd.to_numeric(df['count'], errors='coerce')
            return df
    except mysql.connector.Error as e:
        st.error(f"Error fetching data for frame2: {e}")
        return None

def insert_top_20_ports(date_str, full_dst_counts):
    try:
        with mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        ) as engine:
            cursor = engine.cursor()
            counter = 0
            today_str = datetime.today().strftime("%Y%m%d")
            log_id = f"log_{date_str}"
            if full_dst_counts is not None:
                top_20_ports = full_dst_counts.groupby('dstport')['count'].sum().nlargest(20)
                cursor.execute(
                    "SELECT PORT, COUNT, ID FROM PLOT_DATA WHERE LOG_ID = %s AND LOG_TYPE = %s",
                    (log_id, "PORT")
                )
                existing_ports = {row[0]: {'count': row[1], 'id': row[2]} for row in cursor.fetchall()}
                for port, count in top_20_ports.items():
                    port_str = str(port)
                    count_str = str(int(count))
                    if port_str in existing_ports:
                        if date_str == today_str:
                            update_query = """
                                UPDATE PLOT_DATA
                                SET COUNT = %s
                                WHERE ID = %s AND LOG_ID = %s AND LOG_TYPE = %s AND PORT = %s
                            """
                            cursor.execute(update_query, (count_str, existing_ports[port_str]['id'], log_id, "PORT", port_str))
                    else:
                        unique_id = int(time.time() * 1000000) + counter
                        counter += 1
                        insert_query = """
                            INSERT INTO PLOT_DATA (ID, LOG_ID, LOG_TYPE, DOMAIN, PORT, COUNT)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (unique_id, log_id, "PORT", "N/A", port_str, count_str))
                engine.commit()
    except mysql.connector.Error as e:
        st.error(f"Error inserting/updating top 20 ports: {e}")

def insert_specific_port_data(date_str, selected_port, full_dst_counts):
    try:
        with mysql.connector.connect(
            host="192.168.100.25",
            user="sysuser",
            password="DT1Y9Q0EtBwI0",
            database="syslog"
        ) as engine:
            cursor = engine.cursor()
            counter = 0
            today_str = datetime.today().strftime("%Y%m%d")
            log_id = f"log_{date_str}"
            if full_dst_counts is not None and 'dst' in full_dst_counts.columns:
                filtered_data = full_dst_counts[full_dst_counts['dstport'] == selected_port]
                top_20_ips = filtered_data.groupby('dst')['count'].sum().nlargest(20).reset_index()
                ip_from_df = [ip for ip in top_20_ips['dst'].tolist() if isinstance(ip, str) and ip]
                domains = {}
                if ip_from_df:
                    placeholders = ','.join(['%s'] * len(ip_from_df))
                    cursor.execute(f"SELECT ip, DOMAIN FROM LOG_DNS WHERE ip IN ({placeholders})", ip_from_df)
                    existing_ip_domains = {row[0]: row[1] for row in cursor.fetchall()}
                    for ip in ip_from_df:
                        if ip in existing_ip_domains and existing_ip_domains[ip]:
                            domains[ip] = existing_ip_domains[ip]
                        else:
                            info = insert_ip_info(ip, top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0], ip)
                            domains[ip] = info['domain']
                domain_counts = {}
                for ip, domain in domains.items():
                    if domain:
                        count = top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0]
                        domain_counts[domain] = domain_counts.get(domain, 0) + count
                cursor.execute(
                    "SELECT DOMAIN, COUNT, ID FROM PLOT_DATA WHERE LOG_ID = %s AND PORT = %s AND LOG_TYPE = %s",
                    (log_id, selected_port, "DOMAIN")
                )
                existing_domains = {row[0]: {'count': row[1], 'id': row[2]} for row in cursor.fetchall()}
                for domain, count in domain_counts.items():
                    count_str = str(int(count))
                    if domain in existing_domains:
                        if date_str == today_str:
                            update_query = """
                                UPDATE PLOT_DATA
                                SET COUNT = %s
                                WHERE ID = %s AND LOG_ID = %s AND LOG_TYPE = %s AND PORT = %s AND DOMAIN = %s
                            """
                            cursor.execute(update_query, (count_str, existing_domains[domain]['id'], log_id, "DOMAIN", selected_port, domain))
                    else:
                        unique_id = int(time.time() * 1000000) + counter
                        counter += 1
                        insert_query = """
                            INSERT INTO PLOT_DATA (ID, LOG_ID, LOG_TYPE, DOMAIN, PORT, COUNT)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (unique_id, log_id, "DOMAIN", domain, selected_port, count_str))
                engine.commit()
    except mysql.connector.Error as e:
        st.error(f"Error inserting/updating specific port data: {e}")

# Streamlit app
st.title("Network Traffic visualization using syslog Dashboard")
st.markdown("Interactive dashboard for Network Traffic Visualization using syslog data. Integrated with CRM/self-service portal via database connections. This powerful tool provides real-time insights into network traffic patterns, enabling efficient monitoring and analysis. Features include customizable date selection, detailed IP and port visualizations, and domain hit statistics, all presented in an intuitive interface. Seamlessly embedded into your existing CRM or self-service portal, it supports data-driven decision-making with secure API endpoints for enhanced accessibility")

# Date selection
today = datetime.today()
max_date = today
min_date = today - timedelta(days=10)

# Fetch data if not already in session state
if st.session_state.dst_counts_frame1 is None:
    with st.spinner("Loading data for scatter plot..."):
        st.session_state.dst_counts_frame1 = fetch_data_frame1(st.session_state.selected_date.strftime("%Y%m%d"))
        if st.session_state.dst_counts_frame1 is not None:
            st.session_state.unique_ips = sorted(st.session_state.dst_counts_frame1['dst'].unique())

if st.session_state.full_dst_counts is None:
    with st.spinner("Loading data for bar and pie charts..."):
        date_str_ymd = st.session_state.selected_date.strftime("%Y%m%d")
        st.session_state.full_dst_counts = fetch_data_frame2(date_str_ymd)
        if st.session_state.full_dst_counts is not None:
            port_data = check_plot_data(date_str_ymd, "PORT")
            today_str = today.strftime("%Y%m%d")
            if port_data is not None and date_str_ymd != today_str:
                st.session_state.dst_counts_frame2 = port_data.rename(columns={'dstport': 'dstport', 'count': 'count'})
                st.session_state.unique_dstports = sorted(st.session_state.dst_counts_frame2['dstport'].unique())
            else:
                insert_top_20_ports(date_str_ymd, st.session_state.full_dst_counts)
                st.session_state.dst_counts_frame2 = st.session_state.full_dst_counts.groupby('dstport')['count'].sum().reset_index()
                st.session_state.unique_dstports = sorted(st.session_state.full_dst_counts['dstport'].unique())

# Frame 2: Port and Domain Charts (Side by Side)
st.header("Port vs Domain Count")
col1, col2 = st.columns(2)

with col1:
    selected_date = st.date_input("Select Date", value=st.session_state.selected_date, min_value=min_date, max_value=max_date, key="date_select")
    date_str_ymd = selected_date.strftime("%Y%m%d")
    date_str_hyphen = selected_date.strftime("%Y-%m-%d")
    
    # Update session state with selected date
    if selected_date != st.session_state.selected_date:
        st.session_state.selected_date = selected_date
        st.session_state.dst_counts_frame1 = None
        st.session_state.dst_counts_frame2 = None
        st.session_state.full_dst_counts = None
        st.session_state.unique_ips = []
        st.session_state.unique_dstports = []
        # Re-fetch data
        with st.spinner("Loading data for bar and pie charts..."):
            st.session_state.full_dst_counts = fetch_data_frame2(date_str_ymd)
            if st.session_state.full_dst_counts is not None:
                port_data = check_plot_data(date_str_ymd, "PORT")
                today_str = today.strftime("%Y%m%d")
                if port_data is not None and date_str_ymd != today_str:
                    st.session_state.dst_counts_frame2 = port_data.rename(columns={'dstport': 'dstport', 'count': 'count'})
                    st.session_state.unique_dstports = sorted(st.session_state.dst_counts_frame2['dstport'].unique())
                else:
                    insert_top_20_ports(date_str_ymd, st.session_state.full_dst_counts)
                    st.session_state.dst_counts_frame2 = st.session_state.full_dst_counts.groupby('dstport')['count'].sum().reset_index()
                    st.session_state.unique_dstports = sorted(st.session_state.full_dst_counts['dstport'].unique())
    
    if st.session_state.dst_counts_frame2 is not None:
        top_20 = st.session_state.dst_counts_frame2.nlargest(20, 'count')
        top_20_sorted = top_20.sort_values(by=['count', 'dstport'], ascending=[False, False])
        x_vals = top_20_sorted['dstport'].astype(str)
        y_vals = top_20_sorted['count']
        fig_bar = go.Figure(
            data=[
                go.Bar(
                    x=x_vals,
                    y=y_vals,
                    text=[f"{int(v):,}" for v in y_vals],
                    textposition='auto',
                    marker=dict(color=y_vals, colorscale='YlOrBr'),
                    width=0.8
                )
            ]
        )
        fig_bar.update_layout(
            title=f'Top 20 dstport Counts for {date_str_hyphen}',
            xaxis=dict(title='Destination Port', type='category', tickmode='linear'),
            yaxis=dict(title='Count of Hits'),
            plot_bgcolor='#000000',
            paper_bgcolor='#000000',
            font_color='#FFD700'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("No data available for bar plot.")

with col2:
    selected_port = st.selectbox("Select dstport for Pie Chart", options=["Select a port"] + st.session_state.unique_dstports, key="port_select")
    if selected_port and selected_port != "Select a port":
        domain_data = check_plot_data(date_str_ymd, "DOMAIN", selected_port)
        if domain_data is not None and date_str_ymd != today.strftime("%Y%m%d"):
            domain_counts = dict(zip(domain_data['domain'], domain_data['count']))
        else:
            if st.session_state.full_dst_counts is not None:
                insert_specific_port_data(date_str_ymd, selected_port, st.session_state.full_dst_counts)
                filtered_data = st.session_state.full_dst_counts[st.session_state.full_dst_counts['dstport'] == selected_port]
                if not filtered_data.empty:
                    top_20_ips = filtered_data.groupby('dst')['count'].sum().nlargest(20).reset_index()
                    ip_from_df = [ip for ip in top_20_ips['dst'].tolist() if isinstance(ip, str) and ip]
                    domains = {}
                    if ip_from_df:
                        try:
                            with mysql.connector.connect(
                                host="192.168.100.25",
                                user="sysuser",
                                password="DT1Y9Q0EtBwI0",
                                database="syslog"
                            ) as engine:
                                cursor = engine.cursor()
                                placeholders = ','.join(['%s'] * len(ip_from_df))
                                query = f"SELECT ip, DOMAIN FROM LOG_DNS WHERE ip IN ({placeholders})"
                                cursor.execute(query, ip_from_df)
                                existing_domains = {row[0]: row[1] for row in cursor.fetchall()}
                                for ip in ip_from_df:
                                    if ip in existing_domains and existing_domains[ip]:
                                        domains[ip] = existing_domains[ip]
                                    else:
                                        info = insert_ip_info(ip, top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0], ip)
                                        domains[ip] = info['domain']
                        except mysql.connector.Error as e:
                            st.error(f"Error querying LOG_DNS: {e}")
                            for ip in ip_from_df:
                                info = insert_ip_info(ip, top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0], ip)
                                domains[ip] = info['domain']
                    domain_counts = {}
                    for ip, domain in domains.items():
                        if domain:
                            count = top_20_ips[top_20_ips['dst'] == ip]['count'].iloc[0]
                            domain_counts[domain] = domain_counts.get(domain, 0) + count
                else:
                    domain_counts = {}
            else:
                domain_counts = {}
        
        if domain_counts:
            df_pie = pd.DataFrame(list(domain_counts.items()), columns=['domain', 'count'])
            fig_pie = px.pie(df_pie, values='count', names='domain', color_discrete_sequence=px.colors.sequential.YlOrBr,
                             title=f'Percentage of Domain Hits for dstport {selected_port} on {date_str_hyphen}')
            fig_pie.update_layout(plot_bgcolor='#000000', paper_bgcolor='#000000', font_color='#FFD700')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("No valid domain data available for the selected port.")

# Frame 1: IP Scatter Plot (Moved to the end)
st.header("Destination IP Scatter Plot")
if st.session_state.dst_counts_frame1 is not None:
    selected_ip = st.selectbox("Select Destination IP", options=["Select an IP"] + st.session_state.unique_ips, key="ip_select")
    if selected_ip and selected_ip != "Select an IP":
        insert_ip_info(selected_ip, 0, get_domain_name(selected_ip))
        filtered_data = st.session_state.dst_counts_frame1[st.session_state.dst_counts_frame1['dst'] == selected_ip]
        fig_scatter = px.scatter(filtered_data, x='dstport', y='count', size='count', color='count',
                                 color_continuous_scale='YlOrBr',
                                 title=f'Count vs dstport for IP: {selected_ip}',
                                 labels={'dstport': 'Destination Port', 'count': 'Count'})
        fig_scatter.update_layout(plot_bgcolor='#000000', paper_bgcolor='#000000', font_color='#FFD700')
        st.plotly_chart(fig_scatter, use_container_width=True)
else:
    st.warning("No data available for scatter plot.")