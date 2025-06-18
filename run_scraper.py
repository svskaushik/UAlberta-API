from scrapers.ualberta import UAlbertaScraper

if __name__ == "__main__":
    print("Running UAlberta scraper as a test...")
    scraper = UAlbertaScraper()
    result = scraper.scrape_all()
    print("Scraping complete. Data summary:")
    for key, value in result.items():
        print(f"{key}: {len(value) if value else 0} items")
