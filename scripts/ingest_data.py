import kagglehub
import sqlite3
import pandas as pd
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def validate_and_clean_geo(df):
    """Specific cleaner for the Geolocation dataset to ensure map compatibility."""
    # Ensure numeric types and handle 'coerce' to turn strings into NaNs
    df['geolocation_lat'] = pd.to_numeric(df['geolocation_lat'], errors='coerce')
    df['geolocation_lng'] = pd.to_numeric(df['geolocation_lng'], errors='coerce')
    
    # Drop coordinates outside Brazil's bounding box to keep the map focused
    df = df[
        (df['geolocation_lat'] <= 5.27) & (df['geolocation_lat'] >= -33.75) &
        (df['geolocation_lng'] <= -34.79) & (df['geolocation_lng'] >= -73.99)
    ]
    
    # DEDUPLICATION: Take the average lat/lng per zip code prefix
    df = df.groupby('geolocation_zip_code_prefix').agg({
        'geolocation_lat': 'mean',
        'geolocation_lng': 'mean',
        'geolocation_city': 'first',
        'geolocation_state': 'first'
    }).reset_index()
    
    return df.dropna(subset=['geolocation_lat', 'geolocation_lng'])

def run_ingestion():
    logging.info("🚀 Downloading dataset from Kaggle...")
    try:
        path = kagglehub.dataset_download("olistbr/brazilian-ecommerce")
    except Exception as e:
        logging.error(f"Failed to download dataset: {e}")
        return

    db_dir = os.path.join(os.getcwd(), 'database')
    os.makedirs(db_dir, exist_ok=True)

    db_path = os.path.join(db_dir, 'ecommerce.db')
    conn = sqlite3.connect(db_path)
    
    files_to_load = {
        'olist_customers_dataset.csv': 'customers',
        'olist_orders_dataset.csv': 'orders',
        'olist_order_items_dataset.csv': 'order_items',
        'olist_products_dataset.csv': 'products',
        'olist_sellers_dataset.csv': 'sellers',
        'olist_order_payments_dataset.csv': 'payments',
        'olist_order_reviews_dataset.csv': 'reviews',
        'olist_geolocation_dataset.csv': 'geolocation'
    }

    for file_name, table_name in files_to_load.items():
        full_path = os.path.join(path, file_name)
        
        if os.path.exists(full_path):
            logging.info(f"Processing {file_name}...")
            
            # Use chunking for the large geolocation file to prevent memory spikes
            if table_name == 'geolocation':
                df = pd.read_csv(full_path, low_memory=False)
                df = validate_and_clean_geo(df)
            else:
                df = pd.read_csv(full_path)

            df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            # PERFORMANCE FIX: Create indexes on foreign keys to stop the 'Ambiguous' errors 
            # and speed up the dashboard queries significantly.
            if table_name in ['orders', 'order_items']:
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_order_id ON {table_name} (order_id)")
                
            logging.info(f"✅ Table '{table_name}' loaded ({len(df)} rows).")

    conn.close()
    logging.info(f"✨ ETL Process Complete. Database: {db_path}")

if __name__ == "__main__":
    run_ingestion()