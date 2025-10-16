from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
from threading import Thread
from scraper import UniversalEcommerceScraper

app = Flask(__name__, static_folder='../frontend/build', static_url_path='')
CORS(app)

scraping_status = {
    'is_running': False,
    'progress': 0,
    'message': 'Ready',
    'last_search': None
}

latest_results = []

@app.route('/api/search', methods=['POST'])
def search_products():
    data = request.json
    search_query = data.get('query', '')
    websites = data.get('websites', None)
    
    if not search_query:
        return jsonify({'error': 'Search query is required'}), 400
    
    def scrape_background():
        global scraping_status, latest_results
        scraping_status = {
            'is_running': True,
            'progress': 10,
            'message': 'Initializing scraper...',
            'last_search': search_query
        }
        
        try:
            scraper = UniversalEcommerceScraper(debug_mode=False)
            scraping_status['progress'] = 30
            scraping_status['message'] = 'Scraping products...'
            
            products = scraper.compare_prices(search_query, websites)
            
            scraping_status['progress'] = 90
            scraping_status['message'] = 'Processing results...'
            latest_results = products
            
            scraping_status['progress'] = 100
            scraping_status['message'] = f'Found {len(products)} products'
            scraping_status['is_running'] = False
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'results_{timestamp}.json'
            with open(f'data/{filename}', 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            scraping_status['is_running'] = False
            scraping_status['message'] = f'Error: {str(e)}'
            print(f"Scraping error: {e}")
    
    thread = Thread(target=scrape_background)
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'started', 'message': 'Scraping initiated'})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(scraping_status)

@app.route('/api/results', methods=['GET'])
def get_results():
    return jsonify(latest_results)

@app.route('/api/export', methods=['GET'])
def export_results():
    if not latest_results:
        return jsonify({'error': 'No results available'}), 404
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'export_{timestamp}.json'
    
    with open(f'exports/{filename}', 'w', encoding='utf-8') as f:
        json.dump(latest_results, f, indent=2, ensure_ascii=False)
    
    return jsonify({'filename': filename, 'count': len(latest_results)})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    os.makedirs('exports', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)