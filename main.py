import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
import numpy as np
from scipy import stats
import io
import requests
from datetime import datetime
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings("ignore")

# Configurazione della pagina
st.set_page_config(page_title="Advanced Data Dashboard", layout="wide")

# Sidebar per il tema
theme = st.sidebar.radio("Select Theme:", ["Light", "Dark"])

# Tema CSS
if theme == "Light":
    st.markdown(
        """
    <style>
    :root {
        --bg-primary: #f9fbfd;
        --bg-secondary: #ffffff;
        --text-primary: #1b2a4e;
        --text-secondary: #6e84a3;
        --accent: #2c7be5;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
    <style>
    :root {
        --bg-primary: #0f172a;
        --bg-secondary: #1e293b;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
        --accent: #38bdf8;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

# Titolo della dashboard
st.title("Advanced Sales Analytics Dashboard")


# Funzioni Analitiche Avanzate
def calculate_advanced_metrics(data):
    metrics = {}

    # Trend Analysis
    if "Sales" in data.columns and "Date" in data.columns:
        sales_by_date = data.groupby("Date")["Sales"].sum()
        slope, _, r_value, _, _ = stats.linregress(
            range(len(sales_by_date)), sales_by_date
        )
        metrics["sales_trend"] = "Positive" if slope > 0 else "Negative"
        metrics["trend_strength"] = abs(r_value)

    # Sales Performance
    if "Sales" in data.columns:
        metrics["avg_daily_sales"] = data.groupby("Date")["Sales"].sum().mean()
        metrics["sales_volatility"] = data["Sales"].std() / data["Sales"].mean()

    # Product Performance
    if "Product" in data.columns and "Sales" in data.columns:
        product_performance = data.groupby("Product")["Sales"].agg(
            ["sum", "count", "mean"]
        )
        metrics["top_products"] = product_performance.nlargest(5, "sum").index.tolist()
        metrics["underperforming_products"] = product_performance.nsmallest(
            5, "mean"
        ).index.tolist()

    # Calcolo metriche aggiuntive
    if "Sales" in data.columns and "Profit" in data.columns:
        metrics["profit_margin"] = (data["Profit"].sum() / data["Sales"].sum()) * 100
        metrics["avg_transaction_value"] = data["Sales"].mean()

    return metrics


def perform_customer_segmentation(data):
    if "Customer" not in data.columns:
        return None

    # Preparazione dei dati per clustering
    customer_metrics = (
        data.groupby("Customer")
        .agg(
            {
                "Sales": ["count", "sum", "mean"],
                "Date": lambda x: (x.max() - x.min()).days,
            }
        )
        .reset_index()
    )

    # Standardizzazione
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(customer_metrics.iloc[:, 1:])

    # Clustering
    kmeans = KMeans(n_clusters=3, random_state=42)
    customer_metrics["Segment"] = kmeans.fit_predict(features_scaled)

    return customer_metrics


def detect_anomalies(data):
    if "Sales" not in data.columns:
        return None

    daily_sales = data.groupby("Date")["Sales"].sum()
    sales_mean = daily_sales.mean()
    sales_std = daily_sales.std()

    anomalies = daily_sales[abs(daily_sales - sales_mean) > 2 * sales_std]
    return anomalies


def create_advanced_visualizations(data, container):
    # 1. Sales Performance Overview
    fig1 = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Daily Sales Trend",
            "Sales Distribution",
            "Sales by Region",
            "Top Products",
        ),
    )

    # Daily Sales Trend with Moving Average
    daily_sales = data.groupby("Date")["Sales"].sum().reset_index()
    ma_30 = daily_sales["Sales"].rolling(window=30).mean()

    fig1.add_trace(
        go.Scatter(
            x=daily_sales["Date"],
            y=daily_sales["Sales"],
            name="Daily Sales",
            mode="lines",
        ),
        row=1,
        col=1,
    )
    fig1.add_trace(
        go.Scatter(
            x=daily_sales["Date"], y=ma_30, name="30-Day MA", line=dict(dash="dash")
        ),
        row=1,
        col=1,
    )

    # Sales Distribution
    fig1.add_trace(
        go.Histogram(x=data["Sales"], nbinsx=30, name="Sales Distribution"),
        row=1,
        col=2,
    )

    # Regional Performance
    regional_sales = data.groupby("Region")["Sales"].sum().reset_index()
    fig1.add_trace(
        go.Bar(
            x=regional_sales["Region"], y=regional_sales["Sales"], name="Regional Sales"
        ),
        row=2,
        col=1,
    )

    # Top Products
    product_sales = data.groupby("Product")["Sales"].sum().nlargest(10).reset_index()
    fig1.add_trace(
        go.Bar(
            x=product_sales["Product"], y=product_sales["Sales"], name="Product Sales"
        ),
        row=2,
        col=2,
    )

    fig1.update_layout(height=800, showlegend=True)
    container.plotly_chart(fig1, use_container_width=True)

    # 2. Advanced Analysis Section
    col1, col2 = container.columns(2)

    # Sales Heatmap by Day and Hour
    if "Date" in data.columns:
        data["Hour"] = data["Date"].dt.hour
        data["Day"] = data["Date"].dt.day_name()
        sales_pivot = data.pivot_table(
            values="Sales", index="Day", columns="Hour", aggfunc="mean"
        )

        fig_heatmap = go.Figure(
            data=go.Heatmap(
                z=sales_pivot.values,
                x=sales_pivot.columns,
                y=sales_pivot.index,
                colorscale="Viridis",
            )
        )
        fig_heatmap.update_layout(
            title="Sales Heatmap by Day and Hour",
            xaxis_title="Hour of Day",
            yaxis_title="Day of Week",
        )
        col1.plotly_chart(fig_heatmap, use_container_width=True)

    # Product Performance Scatter
    if "Product" in data.columns:
        product_metrics = (
            data.groupby("Product")
            .agg({"Sales": ["count", "mean"], "Profit": "mean"})
            .reset_index()
        )
        product_metrics.columns = ["Product", "Sales_Count", "Avg_Sales", "Avg_Profit"]

        fig_scatter = go.Figure(
            data=go.Scatter(
                x=product_metrics["Avg_Sales"],
                y=product_metrics["Avg_Profit"],
                mode="markers+text",
                text=product_metrics["Product"],
                textposition="top center",
            )
        )
        fig_scatter.update_layout(
            title="Product Performance Analysis",
            xaxis_title="Average Sales",
            yaxis_title="Average Profit",
        )
        col2.plotly_chart(fig_scatter, use_container_width=True)


# Funzione per caricare dati dall'API
@st.cache_data
def fetch_api_data(api_url):
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            data = pd.DataFrame(response.json())
            if "Date" in data.columns:
                data["Date"] = pd.to_datetime(
                    data["Date"], format="%Y-%m-%d", errors="coerce"
                )
            return data
        else:
            st.error(f"API returned an error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Failed to fetch data from API: {e}")
        return None


# Funzione per filtrare i dati
@st.cache_data
def filter_data(data, filters):
    filtered_data = data.copy()
    for column, filter_value in filters.items():
        if column == "Date" and len(filter_value) == 2:
            start_date, end_date = filter_value
            filtered_data = filtered_data[
                (filtered_data[column] >= pd.to_datetime(start_date))
                & (filtered_data[column] <= pd.to_datetime(end_date))
            ]
        elif filter_value:
            filtered_data = filtered_data[filtered_data[column].isin(filter_value)]
    return filtered_data


# Funzione per calcolare KPI base
def calculate_kpi(data):
    kpis = {}
    kpis["Total Rows"] = len(data)
    if "Sales" in data.columns:
        kpis["Total Sales"] = data["Sales"].sum()
    if "Profit" in data.columns:
        kpis["Total Profit"] = data["Profit"].sum()
    return kpis


# Tabs
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Main Dashboard", "🔍 Advanced Analytics", "⚙️ Settings", "🌐 API Integration"]
)

# Tab 1: Main Dashboard
with tab1:
    st.subheader("Upload Data for Analysis")
    uploaded_file = st.file_uploader(
        "Upload a file (CSV, JSON, or Excel)", type=["csv", "json", "xlsx", "xls"]
    )

    if uploaded_file:
        # Load data based on file type
        file_type = uploaded_file.name.split(".")[-1]
        if file_type == "csv":
            data = pd.read_csv(uploaded_file)
        elif file_type == "json":
            data = pd.read_json(uploaded_file)
        elif file_type in ["xlsx", "xls"]:
            data = pd.read_excel(uploaded_file)
        else:
            st.error("Unsupported file format!")
            data = None

        if data is not None:
            # Conversione colonna Date
            if "Date" in data.columns:
                data["Date"] = pd.to_datetime(data["Date"], errors="coerce")

            # Anteprima file
            st.write("File loaded successfully! Here's a preview:")
            st.dataframe(data.head())

            # Filtri nella sidebar
            st.sidebar.header("Filters")
            filters = {}

            if "Date" in data.columns:
                min_date, max_date = data["Date"].min(), data["Date"].max()
                filters["Date"] = st.sidebar.date_input(
                    "Select Date Range", [min_date, max_date]
                )

            if "Product" in data.columns:
                products = data["Product"].unique()
                filters["Product"] = st.sidebar.multiselect(
                    "Select Products", options=products, default=products
                )

            if "Region" in data.columns:
                regions = data["Region"].unique()
                filters["Region"] = st.sidebar.multiselect(
                    "Select Regions", options=regions, default=regions
                )

            filtered_data = filter_data(data, filters)

            # Basic Metrics
            st.header("Key Metrics")
            kpis = calculate_kpi(filtered_data)
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Rows", kpis.get("Total Rows", 0))
            col2.metric("Total Sales", f"${kpis.get('Total Sales', 0):,.2f}")
            col3.metric("Total Profit", f"${kpis.get('Total Profit', 0):,.2f}")

            # Advanced Metrics
            advanced_metrics = calculate_advanced_metrics(filtered_data)
            st.header("Advanced Metrics")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Sales Trend", advanced_metrics.get("sales_trend", "N/A"))
            col2.metric(
                "Trend Strength", f"{advanced_metrics.get('trend_strength', 0):,.2f}"
            )
            col3.metric(
                "Sales Volatility",
                f"{advanced_metrics.get('sales_volatility', 0):,.2%}",
            )
            col4.metric(
                "Profit Margin", f"{advanced_metrics.get('profit_margin', 0):,.2f}%"
            )

            # Visualizations
            create_advanced_visualizations(filtered_data, st)

            # Export Options
            st.subheader("Export Data")
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "Download Filtered Data (CSV)",
                    filtered_data.to_csv(index=False).encode("utf-8"),
                    "filtered_data.csv",
                    "text/csv",
                )
            with col2:
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                    filtered_data.to_excel(
                        writer, index=False, sheet_name="Filtered Data"
                    )
                st.download_button(
                    "Download Filtered Data (Excel)",
                    data=excel_buffer.getvalue(),
                    file_name="filtered_data.xlsx",
                    mime="application/vnd.ms-excel",
                )

# Tab 2: Advanced Analytics
with tab2:
    st.subheader("Advanced Analytics")
    if "data" in locals():
        # Anomaly Detection
        st.write("### Sales Anomalies")
        anomalies = detect_anomalies(data)
        if anomalies is not None:
            fig_anomalies = go.Figure()
            daily_sales = data.groupby("Date")["Sales"].sum()
            fig_anomalies.add_trace(
                go.Scatter(
                    x=daily_sales.index,
                    y=daily_sales.values,
                    mode="lines",
                    name="Daily Sales",
                )
            )
            fig_anomalies.add_trace(
                go.Scatter(
                    x=anomalies.index,
                    y=anomalies.values,
                    mode="markers",
                    name="Anomalies",
                    marker=dict(color="red", size=10),
                )
            )
            st.plotly_chart(fig_anomalies, use_container_width=True)

        # Customer Segmentation
        st.write("### Customer Segmentation")
        customer_segments = perform_customer_segmentation(data)
        if customer_segments is not None:
            # Continua da customer_segments
            fig_segments = px.scatter(
                customer_segments,
                x="Sales",
                y=("Sales", "mean"),
                color="Segment",
                hover_data=["Customer"],
                title="Customer Segmentation Analysis",
            )
            st.plotly_chart(fig_segments, use_container_width=True)

        # Seasonal Analysis
        if "Date" in data.columns and "Sales" in data.columns:
            st.write("### Seasonal Analysis")
            data["Month"] = data["Date"].dt.month
            data["Quarter"] = data["Date"].dt.quarter
            data["Year"] = data["Date"].dt.year

            # Monthly Trends
            monthly_sales = data.groupby(["Year", "Month"])["Sales"].sum().reset_index()
            fig_monthly = px.line(
                monthly_sales,
                x="Month",
                y="Sales",
                color="Year",
                title="Monthly Sales Trends by Year",
            )
            st.plotly_chart(fig_monthly, use_container_width=True)

            # Quarterly Analysis
            quarterly_sales = (
                data.groupby(["Year", "Quarter"])["Sales"].sum().reset_index()
            )
            fig_quarterly = px.bar(
                quarterly_sales,
                x="Quarter",
                y="Sales",
                color="Year",
                title="Quarterly Sales Analysis",
            )
            st.plotly_chart(fig_quarterly, use_container_width=True)

        # Product Analysis
        if "Product" in data.columns and "Sales" in data.columns:
            st.write("### Product Analysis")

            # Product Performance Matrix
            product_matrix = (
                data.groupby("Product")
                .agg({"Sales": ["sum", "count", "mean"], "Profit": ["sum", "mean"]})
                .round(2)
            )
            product_matrix.columns = [
                "Total Sales",
                "Number of Sales",
                "Avg Sale Value",
                "Total Profit",
                "Avg Profit",
            ]
            st.dataframe(product_matrix)

            # Product Correlation Analysis
            product_pivot = data.pivot_table(
                index="Date", columns="Product", values="Sales", aggfunc="sum"
            ).fillna(0)
            product_corr = product_pivot.corr()

            fig_corr = px.imshow(product_corr, title="Product Sales Correlation Matrix")
            st.plotly_chart(fig_corr, use_container_width=True)

# Tab 3: Settings
with tab3:
    st.subheader("Dashboard Settings")

    # Visual Settings
    st.write("### Visual Settings")
    chart_theme = st.selectbox("Chart Theme", ["plotly", "plotly_white", "plotly_dark"])
    show_animations = st.checkbox("Enable Chart Animations", value=True)

    # Data Processing Settings
    st.write("### Data Processing Settings")
    anomaly_threshold = st.slider("Anomaly Detection Threshold", 1.0, 4.0, 2.0, 0.1)
    customer_segments = st.slider("Number of Customer Segments", 2, 10, 3)

    # Export Settings
    st.write("### Export Settings")
    export_format = st.radio("Default Export Format", ["CSV", "Excel", "JSON"])
    include_metadata = st.checkbox("Include Analysis Metadata in Export", value=True)

    # Save Settings
    if st.button("Save Settings"):
        st.success("Settings saved successfully!")

    # Reset Settings
    if st.button("Reset to Defaults"):
        st.success("Settings reset to defaults!")

# Tab 4: API Integration
with tab4:
    st.subheader("API Data Integration")

    # API Configuration
    st.write("### API Configuration")
    api_url = st.text_input(
        "Enter API Endpoint",
        "https://sales-data-api.onrender.com/generate-sales?num_records=1000",
    )

    # API Authentication (if needed)
    with st.expander("API Authentication"):
        api_key = st.text_input("API Key", type="password")
        api_secret = st.text_input("API Secret", type="password")

    # Fetch Data
    if st.button("Fetch Data from API"):
        with st.spinner("Fetching data..."):
            api_data = fetch_api_data(api_url)
            if api_data is not None:
                st.success("API Data Loaded Successfully!")
                st.dataframe(api_data)

                # Process API data
                if "Date" in api_data.columns:
                    api_data["Date"] = pd.to_datetime(api_data["Date"])

                # Show API data analytics
                st.write("### API Data Analytics")
                create_advanced_visualizations(api_data, st)

                # Export API data
                st.download_button(
                    "Download API Data",
                    api_data.to_csv(index=False).encode("utf-8"),
                    "api_data.csv",
                    "text/csv",
                )

    # API Data Refresh Settings
    st.write("### Auto-Refresh Settings")
    auto_refresh = st.checkbox("Enable Auto-Refresh")
    if auto_refresh:
        refresh_interval = st.number_input(
            "Refresh Interval (minutes)", min_value=1, max_value=60, value=5
        )

# Footer
st.markdown(
    """
---
Created with ❤️ using Streamlit | Last updated: {}
""".format(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
)
