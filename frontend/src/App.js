import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Search, TrendingDown, Filter, Star, Tag, ExternalLink, 
  Package, Zap, Shield, RefreshCw, Loader, AlertCircle,
  Download, X
} from 'lucide-react';
import './App.css';

function App() {
  const [products, setProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [newSearch, setNewSearch] = useState('');
  const [selectedSource, setSelectedSource] = useState('all');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [sortBy, setSortBy] = useState('price_low');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [showSearchModal, setShowSearchModal] = useState(true);
  const [selectedWebsites, setSelectedWebsites] = useState(['flipkart', 'amazon', 'vijay_sales', 'jiomart', 'croma']);

  // Poll for scraping status
  useEffect(() => {
    let interval;
    if (isLoading) {
      interval = setInterval(async () => {
        try {
          const response = await axios.get('/api/status');
          const status = response.data;
          
          setLoadingMessage(status.message);
          
          if (!status.is_running && status.progress === 100) {
            // Scraping complete, fetch results
            const resultsResponse = await axios.get('/api/results');
            setProducts(resultsResponse.data);
            setFilteredProducts(resultsResponse.data);
            setIsLoading(false);
            clearInterval(interval);
          }
        } catch (error) {
          console.error('Error checking status:', error);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  // Filter and sort products
  useEffect(() => {
    let filtered = [...products];

    if (searchTerm) {
      filtered = filtered.filter(p => 
        p.title.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (selectedSource !== 'all') {
      filtered = filtered.filter(p => p.source === selectedSource);
    }

    if (selectedCategory !== 'all') {
      filtered = filtered.filter(p => p.category === selectedCategory);
    }

    if (sortBy === 'price_low') {
      filtered.sort((a, b) => (a.price_num || 0) - (b.price_num || 0));
    } else if (sortBy === 'price_high') {
      filtered.sort((a, b) => (b.price_num || 0) - (a.price_num || 0));
    } else if (sortBy === 'rating') {
      filtered.sort((a, b) => {
        const ratingA = parseFloat(a.rating) || 0;
        const ratingB = parseFloat(b.rating) || 0;
        return ratingB - ratingA;
      });
    }

    setFilteredProducts(filtered);
  }, [searchTerm, selectedSource, selectedCategory, sortBy, products]);

  const handleSearch = async () => {
    if (!newSearch.trim()) {
      alert('Please enter a search query');
      return;
    }

    setIsLoading(true);
    setShowSearchModal(false);
    setLoadingMessage('Starting search...');

    try {
      await axios.post('/api/search', {
        query: newSearch,
        websites: selectedWebsites.length === 5 ? null : selectedWebsites
      });
    } catch (error) {
      console.error('Search error:', error);
      setIsLoading(false);
      alert('Error starting search. Please try again.');
    }
  };

  const handleExport = async () => {
    try {
      const response = await axios.get('/api/export');
      alert(`Results exported: ${response.data.filename}`);
    } catch (error) {
      console.error('Export error:', error);
      alert('Error exporting results');
    }
  };

  const toggleWebsite = (website) => {
    if (selectedWebsites.includes(website)) {
      setSelectedWebsites(selectedWebsites.filter(w => w !== website));
    } else {
      setSelectedWebsites([...selectedWebsites, website]);
    }
  };

  const getSourceColor = (source) => {
    const colors = {
      'Flipkart': 'bg-yellow-500',
      'Amazon': 'bg-orange-500',
      'Vijay Sales': 'bg-red-500',
      'JioMart': 'bg-blue-500',
      'Croma': 'bg-green-500'
    };
    return colors[source] || 'bg-gray-500';
  };

  const sources = ['all', ...new Set(products.map(p => p.source))];
  const categories = ['all', ...new Set(products.map(p => p.category))];

  const bestDeal = filteredProducts.length > 0 && filteredProducts[0].price_num ? 
    filteredProducts.reduce((min, p) => (p.price_num && p.price_num < (min.price_num || Infinity)) ? p : min) : null;

  return (
    <div className="App">
      {/* Search Modal */}
      {showSearchModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>🔍 Start Your Price Comparison</h2>
              <button onClick={() => setShowSearchModal(false)} className="close-btn">
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <div className="modal-body">
              <label>What are you looking for?</label>
              <input
                type="text"
                placeholder="e.g., iPhone 15, Samsung TV, Nike Shoes..."
                value={newSearch}
                onChange={(e) => setNewSearch(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="search-input"
              />

              <label className="mt-4">Select Websites to Compare:</label>
              <div className="website-grid">
                {[
                  { id: 'flipkart', name: 'Flipkart', color: 'yellow' },
                  { id: 'amazon', name: 'Amazon', color: 'orange' },
                  { id: 'vijay_sales', name: 'Vijay Sales', color: 'red' },
                  { id: 'jiomart', name: 'JioMart', color: 'blue' },
                  { id: 'croma', name: 'Croma', color: 'green' }
                ].map(site => (
                  <button
                    key={site.id}
                    onClick={() => toggleWebsite(site.id)}
                    className={`website-btn ${selectedWebsites.includes(site.id) ? 'selected' : ''} ${site.color}`}
                  >
                    {site.name}
                  </button>
                ))}
              </div>

              <button onClick={handleSearch} className="search-btn">
                <Search className="w-5 h-5" />
                <span>Start Comparison</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {isLoading && (
        <div className="loading-overlay">
          <div className="loading-content">
            <Loader className="loading-spinner" />
            <h3>Searching Products...</h3>
            <p>{loadingMessage}</p>
            <div className="loading-bar">
              <div className="loading-progress"></div>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="header">
        <div className="container">
          <div className="header-content">
            <div className="logo">
              <div className="logo-icon">
                <TrendingDown className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1>ShopSmart</h1>
                <p>Compare prices across 5+ platforms</p>
              </div>
            </div>
            <button onClick={() => setShowSearchModal(true)} className="new-search-btn">
              <RefreshCw className="w-4 h-4" />
              <span>New Search</span>
            </button>
          </div>
        </div>
      </header>

      {/* USP Banner */}
      <div className="usp-banner">
        <div className="container">
          <div className="usp-grid">
            <div className="usp-card">
              <Zap className="w-8 h-8" />
              <div>
                <div className="usp-title">Real-Time Prices</div>
                <div className="usp-subtitle">Always up-to-date</div>
              </div>
            </div>
            <div className="usp-card">
              <Package className="w-8 h-8" />
              <div>
                <div className="usp-title">5+ Platforms</div>
                <div className="usp-subtitle">All in one place</div>
              </div>
            </div>
            <div className="usp-card">
              <Shield className="w-8 h-8" />
              <div>
                <div className="usp-title">100% Free</div>
                <div className="usp-subtitle">No hidden costs</div>
              </div>
            </div>
            <div className="usp-card">
              <TrendingDown className="w-8 h-8" />
              <div>
                <div className="usp-title">Best Deals</div>
                <div className="usp-subtitle">Save up to 40%</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Best Deal */}
      {bestDeal && (
        <div className="container">
          <div className="best-deal">
            <div>
              <div className="best-deal-header">
                <TrendingDown className="w-6 h-6" />
                <span>🏆 BEST DEAL FOUND!</span>
              </div>
              <h3>{bestDeal.title}</h3>
              <div className="best-deal-price">
                <span className="price">{bestDeal.price}</span>
                <span className="source">on {bestDeal.source}</span>
              </div>
            </div>
            <a href={bestDeal.url} target="_blank" rel="noopener noreferrer" className="view-deal-btn">
              <span>View Deal</span>
              <ExternalLink className="w-5 h-5" />
            </a>
          </div>
        </div>
      )}

      {/* Filters */}
      {products.length > 0 && (
        <div className="container">
          <div className="filters">
            <div className="filter-grid">
              <div className="filter-group">
                <label>
                  <Search className="w-4 h-4" />
                  Search Products
                </label>
                <input
                  type="text"
                  placeholder="Search..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="filter-input"
                />
              </div>
              
              <div className="filter-group">
                <label>
                  <Filter className="w-4 h-4" />
                  Website
                </label>
                <select
                  value={selectedSource}
                  onChange={(e) => setSelectedSource(e.target.value)}
                  className="filter-select"
                >
                  {sources.map(s => (
                    <option key={s} value={s}>
                      {s === 'all' ? 'All Websites' : s}
                    </option>
                  ))}
                </select>
              </div>

              <div className="filter-group">
                <label>
                  <Package className="w-4 h-4" />
                  Category
                </label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="filter-select"
                >
                  {categories.map(c => (
                    <option key={c} value={c}>
                      {c === 'all' ? 'All Categories' : c}
                    </option>
                  ))}
                </select>
              </div>

              <div className="filter-group">
                <label>
                  <TrendingDown className="w-4 h-4" />
                  Sort By
                </label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="filter-select"
                >
                  <option value="price_low">Price: Low to High</option>
                  <option value="price_high">Price: High to Low</option>
                  <option value="rating">Top Rated</option>
                </select>
              </div>
            </div>

            <div className="filter-stats">
              <span>Showing <strong>{filteredProducts.length}</strong> products</span>
              <button onClick={handleExport} className="export-btn">
                <Download className="w-4 h-4" />
                Export Results
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Product Grid */}
      <div className="container">
        {products.length === 0 && !isLoading && (
          <div className="empty-state">
            <Package className="w-16 h-16" />
            <h3>No products yet</h3>
            <p>Click "New Search" to start comparing prices</p>
            <button onClick={() => setShowSearchModal(true)} className="start-btn">
              Start Shopping
            </button>
          </div>
        )}

        <div className="product-grid">
          {filteredProducts.map((product, idx) => (
            <div key={idx} className="product-card">
              <div className="product-image">
                <img src={product.image !== 'N/A' ? product.image : 'https://via.placeholder.com/400x400?text=No+Image'} alt={product.title} />
                <div className={`source-badge ${getSourceColor(product.source)}`}>
                  {product.source}
                </div>
                {product.offers !== 'N/A' && (
                  <div className="offer-badge">
                    <Tag className="w-3 h-3" />
                    <span>OFFERS</span>
                  </div>
                )}
              </div>

              <div className="product-info">
                <h3>{product.title}</h3>

                <div className="product-price-section">
                  <div>
                    <div className="product-price">{product.price}</div>
                    <div className="product-category">{product.category}</div>
                  </div>
                  {product.rating !== 'N/A' && (
                    <div className="product-rating">
                      <Star className="w-4 h-4 fill-current" />
                      <span>{product.rating.split(' ')[0]}</span>
                    </div>
                  )}
                </div>

                {product.offers !== 'N/A' && (
                  <div className="product-offers">
                    <Tag className="w-4 h-4" />
                    <p>{product.offers}</p>
                  </div>
                )}

                <a href={product.url} target="_blank" rel="noopener noreferrer" className="view-btn">
                  <span>View on {product.source}</span>
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <footer className="footer">
        <div className="container">
          <div className="footer-content">
            <TrendingDown className="w-6 h-6" />
            <span className="footer-title">ShopSmart</span>
          </div>
          <p>Compare prices across Flipkart, Amazon, Vijay Sales, JioMart & Croma</p>
          <p className="footer-copyright">© 2025 ShopSmart. All rights reserved. Made with ❤️ for smart shoppers.</p>
        </div>
      </footer>
    </div>
  );
}

export default App;