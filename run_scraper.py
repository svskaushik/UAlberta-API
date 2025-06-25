from scrapers.ualberta import UAlbertaScraper
from database.models import db_manager
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    print("Setting up database...")
    
    # Initialize database tables
    db_manager.create_tables()
    print("Database tables created/verified.")
    
    print("Running UAlberta scraper with database backend...")
    scraper = UAlbertaScraper()
    
    try:
        result = scraper.scrape_all()
        print("Scraping complete. Data summary:")
        for key, value in result.items():
            if isinstance(value, dict):
                print(f"{key}: {len(value)} items")
            elif isinstance(value, list):
                print(f"{key}: {len(value)} items")
            else:
                print(f"{key}: {value}")
    except Exception as e:
        print(f"Scraping failed: {e}")
        raise
