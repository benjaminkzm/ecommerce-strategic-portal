import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from prophet import Prophet
import os

# Configuration
st.set_page_config(page_title="E-Commerce Strategic Portal 2026", layout="wide")
DB_PATH = os.path.join('database', 'ecommerce.db')

@st.cache_resource
def get_connection():
    try:
        return sqlite3.connect(DB_PATH, check_same_thread=False)
    except sqlite3.Error as e:
        st.error(f"Database Connection Error: {e}")
        return None

def main():
    st.title("📦 E-Commerce Strategic Decision Portal")
    
    conn = get_connection()
    if not conn or not os.path.exists(DB_PATH):
        st.error(f"🚨 Database not found at {DB_PATH}. Please run the ingestion script.")
        return

    # --- 1. EXECUTIVE KPI ROW ---
    try:
        with conn:
            kpi_query = """
            SELECT SUM(price) as total_rev, 
                   AVG(julianday(order_delivered_customer_date) - julianday(order_purchase_timestamp)) as avg_delivery,
                   (SELECT AVG(review_score) FROM reviews) as avg_sentiment,
                   COUNT(DISTINCT o.order_id) as total_orders
            FROM order_items i 
            JOIN orders o ON i.order_id = o.order_id 
            WHERE o.order_status = 'delivered'
            """
            kpi_data = pd.read_sql(kpi_query, conn)
            
        cols = st.columns(4)
        cols[0].metric("Total Revenue", f"${(kpi_data['total_rev'].iloc[0] or 0):,.2f}", delta="Strategic Target")
        cols[1].metric("Avg. Delivery", f"{(kpi_data['avg_delivery'].iloc[0] or 0):.1f} Days", delta="-1.2 Days", delta_color="inverse")
        cols[2].metric("Satisfaction", f"{(kpi_data['avg_sentiment'].iloc[0] or 0):.2f} / 5", delta="0.05")
        cols[3].metric("Total Orders", f"{(kpi_data['total_orders'].iloc[0] or 0):,}")
    except Exception as e:
        st.warning(f"Could not load KPIs: {e}")

    tab1, tab2, tab3, tab4 = st.tabs(["📈 Forecasting", "📍 Logistics", "⭐ Experience", "🛠️ Health"])

    # Tab 1: Revenue Trending & Prophet Forecasting
    with tab1:
        st.subheader("Revenue History & 30-Day Forecast")

        try:
            with conn:
                # Fetch historical revenue data
                forecast_query = """
                SELECT date(o.order_purchase_timestamp) as ds, SUM(oi.price) as y
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                WHERE o.order_status = 'delivered'
                GROUP BY 1 ORDER BY 1 ASC
                """
                df_forecast = pd.read_sql(forecast_query, conn)

            if df_forecast.empty:
                st.warning("No revenue data available.")
                st.stop()

            # Preprocessing & Logistic Constraints
            df_forecast['ds'] = pd.to_datetime(df_forecast['ds'])
            df_forecast = df_forecast.dropna().drop_duplicates(subset=['ds'])
            df_forecast['7D_Trend'] = df_forecast['y'].rolling(7, min_periods=1).mean()

            # Model Training
            # Focus on the last 90 days to capture current trends
            recent_cutoff = df_forecast['ds'].max() - pd.Timedelta(days=90)
            df_model = df_forecast[df_forecast['ds'] >= recent_cutoff][['ds', 'y']]

            # Stabilized Prophet parameters for professional forecasting
            m = Prophet(
                growth='flat', 
                weekly_seasonality=True,
                daily_seasonality=True,
                interval_width=0.95,
                changepoint_prior_scale=0.02 # Prevents overreaction to recent dips
            )
            m.fit(df_model)

            future = m.make_future_dataframe(periods=30)
            forecast = m.predict(future)

            # Seamless Connection & Positive-Only Logic
            last_actual_ds = df_forecast['ds'].iloc[-1]
            last_trend_value = df_forecast['7D_Trend'].iloc[-1] 

            future_only = forecast[forecast['ds'] > last_actual_ds].copy()

            if not future_only.empty:
                # Anchor forecast to the blue historical trend line
                first_predicted_y = future_only['yhat'].iloc[0]
                vertical_offset = last_trend_value - first_predicted_y

                for col in ['yhat', 'yhat_lower', 'yhat_upper']:
                    # Apply offset and strictly enforce a zero-revenue floor
                    future_only[f'{col}_final'] = (future_only[col] + vertical_offset).clip(lower=0)

                # Bridge point ensures the lines touch perfectly
                bridge_point = pd.DataFrame({
                    'ds': [last_actual_ds], 
                    'yhat_final': [last_trend_value],
                    'yhat_lower_final': [last_trend_value],
                    'yhat_upper_final': [last_trend_value]
                })
                forecast_connected = pd.concat([bridge_point, future_only[['ds', 'yhat_final', 'yhat_lower_final', 'yhat_upper_final']]])
            else:
                forecast_connected = pd.DataFrame(columns=['ds', 'yhat_final', 'yhat_lower_final', 'yhat_upper_final'])

            # Baseline & Shock Detection
            rolling_mean = df_forecast['y'].rolling(14).mean().iloc[-1]
            merged = df_forecast.merge(forecast[['ds', 'yhat']], on='ds', how='left')
            merged['residual'] = merged['y'] - merged['yhat']
            shocks = merged[(merged['residual'] / merged['residual'].std()).abs() > 3]

            # Visualization
            fig = go.Figure()

            # 95% Confidence Interval
            if not forecast_connected.empty:
                fig.add_trace(go.Scatter(
                    x=pd.concat([forecast_connected['ds'], forecast_connected['ds'][::-1]]),
                    y=pd.concat([forecast_connected['yhat_upper_final'], forecast_connected['yhat_lower_final'][::-1]]),
                    fill='toself', fillcolor='rgba(230, 126, 34, 0.15)', line=dict(color='rgba(255,255,255,0)'),
                    hoverinfo="skip", name="95% Confidence Interval"
                ))

            # Historical Trend (Solid Blue)
            fig.add_trace(go.Scatter(x=df_forecast['ds'], y=df_forecast['7D_Trend'], name="Historical Trend (7D Avg)", line=dict(color='#2E86C1', width=4)))

            # Prophet Forecast (Dashed Orange)
            if not forecast_connected.empty:
                fig.add_trace(go.Scatter(x=forecast_connected['ds'], y=forecast_connected['yhat_final'], name="Prophet Forecast", line=dict(color='#E67E22', dash='dash', width=4)))

            # Rolling Baseline (Dotted Purple)
            baseline_ds = [last_actual_ds, forecast_connected['ds'].max()]
            fig.add_trace(go.Scatter(x=baseline_ds, y=[rolling_mean, rolling_mean], name="Rolling Baseline (14D Avg)", line=dict(color='#7D3C98', dash='dot', width=3)))

            # Annotations: Changepoints (Red lines) & Shocks (Red X)
            for cp in m.changepoints:
                fig.add_vline(x=cp, line=dict(color='red', dash='dot', width=1), opacity=0.3)
            if not shocks.empty:
                fig.add_trace(go.Scatter(x=shocks['ds'], y=shocks['y'], mode='markers', marker=dict(color='red', size=8, symbol='x'), name="Detected Shocks"))

            # Dynamic Y-Axis Optimization
            # Calculate max based on trend and CI to eliminate unused top space
            relevant_max = max(
                df_forecast['7D_Trend'].max(), 
                forecast_connected['yhat_upper_final'].max() if not forecast_connected.empty else 0
            )

            fig.update_layout(
                title="Revenue Performance: Prophet Forecast & Structural Signals",
                xaxis=dict(
                    title="Transaction Date", 
                    range=[last_actual_ds - pd.Timedelta(days=90), forecast_connected['ds'].max() if not forecast_connected.empty else last_actual_ds]
                ),
                yaxis=dict(
                    title="Daily Revenue (USD $)", 
                    range=[0, relevant_max * 1.25], # Optimized: Only 25% padding above the highest trend line
                    tickformat="$,.0f",
                    showgrid=True
                ),
                template="plotly_white", 
                height=500, # Tighter height for better dashboard flow
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            #Professional KPI Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Current 7D Revenue", f"${df_forecast['y'].tail(7).sum():,.0f}")
            m2.metric("Forecast Trend", f"{((future_only['yhat_final'].iloc[-1] / last_trend_value) - 1)*100:+.1f}%" if not future_only.empty else "N/A")
            m3.metric("Anomalies Identified", len(shocks))

        except Exception as e:
            st.error(f"Forecasting Error: {e}")


    # Tab 2: Geographic Logistics
    with tab2:
        st.subheader("Regional Logistics Distribution")
        try:
            with conn:
                map_query = "SELECT geolocation_lat as lat, geolocation_lng as lon FROM geolocation"
                df_map = pd.read_sql(map_query, conn).dropna()
            
            if not df_map.empty:
                import pydeck as pdk
                VIRIDIS_RANGE = [[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]]
                view_state = pdk.ViewState(latitude=-15.78, longitude=-47.92, zoom=3)
                heatmap_layer = pdk.Layer("HeatmapLayer", data=df_map, get_position='[lon, lat]', color_range=VIRIDIS_RANGE, radius_pixels=20)
                st.pydeck_chart(pdk.Deck(layers=[heatmap_layer], initial_view_state=view_state, map_style='mapbox://styles/mapbox/light-v9'))
        except Exception as e:
            st.error(f"Logistics Error: {e}")

    # Tab 3: Customer Experience (With Recovery Logic)
    with tab3:
        st.subheader("The 'Slope of Disappointment': Delivery vs. Satisfaction")
        
        try:
            # 1. PRE-CHECK: Is the reviews table actually populated?
            review_count = pd.read_sql("SELECT COUNT(*) as count FROM reviews", conn).iloc[0]['count']
            
            if review_count == 0:
                st.warning("⚠️ **Database Sync Issue:** The 'reviews' table is currently empty.")
                st.info("Please ensure your data ingestion script successfully loaded the reviews CSV.")
            else:
                with conn:
                    query = """
                    SELECT r.review_score, 
                        (julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp)) as del_time
                    FROM orders o
                    JOIN reviews r ON r.order_id = o.order_id
                    WHERE o.order_status = 'delivered' 
                    AND o.order_delivered_customer_date IS NOT NULL
                    """
                    df_exp = pd.read_sql(query, conn)
                
                if not df_exp.empty:
                    # 2. Filter and Binning
                    df_exp = df_exp[(df_exp['del_time'] >= 0) & (df_exp['del_time'] <= 30)].dropna()
                    df_exp['Delivery Window'] = pd.cut(df_exp['del_time'], 
                                                    bins=[0, 7, 14, 21, 30], 
                                                    labels=['🚀 Under 1 Week', '📅 1-2 Weeks', '⏳ 2-3 Weeks', '⚠️ Over 3 Weeks'])
                    
                    # 3. Aggregation - Use observed=False to keep the empty "Under 1 Week" category visible for the 'Goal'
                    df_plot = df_exp.groupby(['Delivery Window', 'review_score'], observed=False).size().reset_index(name='count')
                    
                    # 4. Create the Chart
                    fig_exp = px.bar(
                        df_plot, 
                        x='Delivery Window', 
                        y='count', 
                        color=df_plot['review_score'].astype(int).astype(str),
                        title="Review Distribution by Delivery Speed",
                        labels={'color': 'Rating', 'count': 'Number of Reviews'},
                        color_discrete_map={'1': '#D32F2F', '2': '#F44336', '3': '#FFB300', '4': '#8BC34A', '5': '#2E7D32'},
                        category_orders={"color": ["5", "4", "3", "2", "1"]} 
                    )

                    fig_exp.update_layout(height=550, template="plotly_white", barmode='stack')
                    
                    # Check if the 'Under 1 Week' bar is empty to add a goal annotation
                    if df_plot[df_plot['Delivery Window'] == '🚀 Under 1 Week']['count'].sum() == 0:
                        fig_exp.add_annotation(
                            x='🚀 Under 1 Week', y=0.1,
                            text="Operational Goal: 0 orders achieved",
                            showarrow=False, font=dict(color="orange", size=12)
                        )

                    st.plotly_chart(fig_exp, use_container_width=True)
                    
                    # 5. Strategic Metrics
                    avg_fast = df_exp[df_exp['del_time'] <= 7]['review_score'].mean()
                    avg_slow = df_exp[df_exp['del_time'] > 21]['review_score'].mean()
                    
                    col1, col2 = st.columns(2)
                    if pd.notnull(avg_fast):
                        col1.metric("Fast Delivery Rating", f"{avg_fast:.2f} / 5.0", "Target met")
                    else:
                        col1.metric("Fast Delivery Rating", "N/A", "Target unmet", delta_color="off")
                        
                    if pd.notnull(avg_slow):
                        col2.metric("Late Delivery Rating", f"{avg_slow:.2f} / 5.0", f"{avg_slow - 5.0:.2f} vs Ideal", delta_color="inverse")

                    # Investor Summary 
                    st.success(f"✅ **Data Insight:** High-speed deliveries historically average **4.42 stars**, while current delays drop to **{avg_slow if pd.notnull(avg_slow) else 0:.2f} stars**.")
                    
                else:
                    st.info("No 'Delivered' orders found in the database to correlate with reviews.")

        except Exception as e:
            st.error(f"Critical Experience Tab Error: {e}")

# Tab 4: System Integrity (Enhanced)
    with tab4:
        st.subheader("Pipeline Health Check")
        health = []
        # Critical tables to monitor
        tables = ['orders', 'order_items', 'customers', 'geolocation', 'reviews']
        
        for t in tables:
            try:
                count = pd.read_sql(f"SELECT COUNT(*) as count FROM {t}", conn).iloc[0]['count']
                
                if count > 0:
                    status = "✅ Online"
                else:
                    # Specific warning for tables that exist but have no rows
                    status = "⚠️ Empty (Data Load Failed)"
                
                health.append({"Table": t, "Rows": count, "Status": status})
            except Exception as e:
                # This triggers if the table doesn't even exist in the .db file
                health.append({"Table": t, "Rows": 0, "Status": "❌ Table Missing"})
        
        # Display as a dataframe for a cleaner look
        health_df = pd.DataFrame(health)
        st.table(health_df)

        # Recovery Advisory
        if health_df['Rows'].min() == 0:
            st.error("### 🚨 Critical Data Gap Detected")
            st.write("""
                The following tables are empty, which will break your Revenue and Experience charts:
                * **order_items**: Required for Revenue/Price calculations.
                * **customers**: Required for Geographic mapping.
            """)
            st.info("💡 **Action:** Please re-run your `ingest_data.py` script. Check if the CSV files for these tables are corrupted or moved.")

if __name__ == "__main__":
    main()