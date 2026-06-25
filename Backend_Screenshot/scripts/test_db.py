from services.db_service import get_all_results

try:
    results = get_all_results()
    print(f"Successfully connected to database. Found {len(results)} results.")
    if results:
        print("First few results:")
        for i, r in enumerate(results[:3]):
            print(f"  {i+1}. ID: {r['id']}, URL: {r['url']}, Status: {r['status']}")
    else:
        print("No results found in database.")
except Exception as e:
    print(f"Database connection failed: {e}")
    import traceback
    traceback.print_exc()