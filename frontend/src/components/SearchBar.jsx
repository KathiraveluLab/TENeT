/**
 * Search Bar Component
 * 
 * Allows users to search communities by name with dropdown results
 */

import React, { useState, useRef, useEffect } from 'react'
import '../styles/search-bar.css'

const SearchBar = ({ onSearch, onClear, onCommunitySelect }) => {
  const [query, setQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [searchResults, setSearchResults] = useState([])
  const [allCommunities, setAllCommunities] = useState([])
  const [showResults, setShowResults] = useState(false)
  const searchRef = useRef(null)

  // Fetch all communities on mount
  useEffect(() => {
    const fetchAllCommunities = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/communities')
        const data = await response.json()
        setAllCommunities(Array.isArray(data) ? data : [])
      } catch (error) {
        console.error('Failed to fetch communities:', error)
        setAllCommunities([])
      }
    }
    fetchAllCommunities()
  }, [])

  // Handle click outside to close results
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowResults(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSearch = async (e) => {
    e.preventDefault()
    if (query.trim().length < 2) return

    setIsSearching(true)
    try {
      const response = await fetch(`http://localhost:8000/api/communities/search?q=${encodeURIComponent(query)}`)
      const results = await response.json()
      setSearchResults(Array.isArray(results) ? results : [])
      setShowResults(true)
      onSearch(Array.isArray(results) ? results : [], query)
    } catch (error) {
      console.error('Search failed:', error)
      setSearchResults([])
      onSearch([], query)
    } finally {
      setIsSearching(false)
    }
  }

  const handleInputChange = async (e) => {
    const value = e.target.value
    setQuery(value)

    // Auto-search as user types (debounced)
    if (value.trim().length >= 2) {
      setIsSearching(true)
      try {
        const response = await fetch(`http://localhost:8000/api/communities/search?q=${encodeURIComponent(value)}`)
        const results = await response.json()
        const resultsArray = Array.isArray(results) ? results : []
        setSearchResults(resultsArray)
        setShowResults(true)
        onSearch(resultsArray, value)
      } catch (error) {
        console.error('Search failed:', error)
        setSearchResults([])
      } finally {
        setIsSearching(false)
      }
    } else {
      setSearchResults([])
      setShowResults(false)
      if (value.trim().length === 0) {
        onClear()
      }
    }
  }

  const handleClear = () => {
    setQuery('')
    setSearchResults([])
    setShowResults(false)
    onClear()
  }

  const handleResultClick = (community) => {
    setShowResults(false)
    setQuery(community.name)
    onCommunitySelect(community.community_id)
  }

  const handleFocus = () => {
    if (query.trim().length === 0) {
      // Show all communities when focusing on empty search
      setSearchResults(allCommunities)
      setShowResults(true)
    } else if (searchResults.length > 0) {
      setShowResults(true)
    }
  }

  const displayResults = query.trim().length === 0 ? allCommunities : searchResults

  return (
    <div className="search-bar" ref={searchRef}>
      <form onSubmit={handleSearch} className="search-form">
        <div className="search-input-wrapper">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            className="search-input"
            placeholder="Search communities..."
            value={query}
            onChange={handleInputChange}
            onFocus={handleFocus}
            disabled={isSearching}
          />
          {query && (
            <button
              type="button"
              className="clear-button"
              onClick={handleClear}
              aria-label="Clear search"
            >
              ×
            </button>
          )}
        </div>
      </form>

      {showResults && displayResults.length > 0 && (
        <div className="search-results">
          <div className="search-results-header">
            {query.trim().length === 0 
              ? `All Communities (${displayResults.length})`
              : `${displayResults.length} ${displayResults.length === 1 ? 'result' : 'results'} found`
            }
          </div>
          <ul className="search-results-list">
            {displayResults.map((community) => (
              <li
                key={community.community_id}
                className="search-result-item"
                onClick={() => handleResultClick(community)}
              >
                <div className="result-name">📍 {community.name}</div>
                <div className="result-details">
                  <span className="result-region">{community.region}</span>
                  {community.population && (
                    <span className="result-population">Pop: {community.population.toLocaleString()}</span>
                  )}
                </div>
                {community.access_tier && (
                  <span className={`result-tier tier-${community.access_tier}`}>
                    Tier {community.access_tier}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {showResults && query.trim().length >= 2 && displayResults.length === 0 && !isSearching && (
        <div className="search-results">
          <div className="search-no-results">
            No communities found for "{query}"
          </div>
        </div>
      )}
    </div>
  )
}

export default SearchBar
