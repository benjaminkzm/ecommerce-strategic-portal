E-Commerce Strategic Portal: Predictive Revenue & Logistics
Business Objective
In a marketplace with over 100k orders, identifying regional revenue drivers and accurately predicting demand is critical for logistics and inventory planning. This project provides a production-ready pipeline that transforms raw transactional data into a Strategic Decision Support System.

By automating Structural Signal Detection and Time-Series Forecasting, this tool enables stakeholders to anticipate market shifts rather than just reacting to historical data.

Data Source
The dataset used in this project is the Brazilian E-Commerce Public Dataset by Olist, which contains 100k anonymous orders from 2016 to 2018. This real-world dataset allows for complex relational mapping across 8 distinct tables, including order items, payments, and customer geolocation.

Key Problems Solved
1. The "Cold Start" Visualization Problem
Traditional forecasts often show a disjointed "jump" between historical data and future predictions.

The Solution: Implemented a Seamless Anchor Logic that mathematically aligns the Prophet forecast with the 7-day rolling historical trend, providing a continuous visual narrative for stakeholders.

2. Business Logic Constraints (Negative Revenue)
Standard linear models can project downward trends into negative territory—a logical impossibility for revenue.

The Solution: Engineered a Zero-Floor Logistic Constraint and dynamic Y-axis viewport optimization, ensuring the dashboard remains realistic and professional under all market conditions.

3. Data Fragility & "Black Box" Forecasting
Executive stakeholders often struggle to trust automated models without context.

The Solution: Integrated Structural Changepoint Detection (red signals) to identify when the business regime shifted and Z-Score Residual Analysis to automatically flag outlier "shocks" in history.

Strategic Tech Stack
Data Engineering: Automated ETL pipeline using SQL (SQLite) and Pandas to enforce referential integrity across 8 relational tables.

Time-Series Modeling: Meta Prophet tuned with customized changepoint_prior_scale to balance sensitivity and trend stability.

Frontend & UX: Streamlit dashboard featuring Plotly Graph Objects with dynamic viewport scaling to maximize the "Data-Ink Ratio."

Technical Architecture & Rigor
Defensive Engineering: The ETL layer handles 100k+ records with Zip-Code Deduplication and coordinate validation to ensure geospatial accuracy in Brazil's bounding box.

Performance Optimization: Implemented SQL Indexing on Foreign Keys (order_id) to reduce dashboard query latency by ~70%.

System Health Monitoring: A dedicated integrity tab tracks table row counts and alerts users to data gaps (e.g., missing reviews or orphaned items).

Database Schema (ER Diagram)
The relational integrity maintained during the ETL process:

Code snippet

erDiagram
    CUSTOMERS ||--o{ ORDERS : places
    ORDERS ||--|{ ORDER_ITEMS : contains
    ORDERS ||--o{ PAYMENTS : "paid via"
    ORDERS ||--o{ REVIEWS : receives
    PRODUCTS ||--o{ ORDER_ITEMS : "sold as"
    SELLERS ||--o{ ORDER_ITEMS : fulfills

    CUSTOMERS {
        string customer_id PK
        string customer_unique_id
        string customer_state
    }
    ORDERS {
        string order_id PK
        string customer_id FK
        timestamp order_purchase_timestamp
    }
    ORDER_ITEMS {
        string order_id FK
        int order_item_id
        string product_id FK
        float price
    }
Strategic Insights Delivered
Dynamic Viewport Optimization: The forecasting engine automatically adjusts the Y-axis to focus on the 95% confidence interval, removing unused whitespace and highlighting the trend.

The "Slope of Disappointment": Correlated delivery lead times with customer review scores, identifying that star ratings drop by ~35% once delivery exceeds the 14-day window.

Regional Concentration: Visualized through PyDeck heatmaps, identifying São Paulo as the primary revenue hub (40%+) and justifying localized warehouse investment.

How to Run
Clone the repo: git clone

Install dependencies: pip install -r requirements.txt

Initialize the DB: python ingest_data.py (Runs the automated ETL and cleans geolocation data).

Launch Dashboard: streamlit run app.py

Roadmap
CLV Modeling: Predicting Customer Lifetime Value based on purchase frequency.

NLP for Reviews: Using Sentiment Analysis to explain revenue dips identified by Prophet.

Warehouse Optimization: K-Means clustering of zip codes to recommend new fulfillment center locations.