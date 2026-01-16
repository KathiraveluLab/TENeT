/**
 * Search Bar Component
 * 
 * Allows users to search communities by name with dropdown results
 */

import React, { useState, useRef, useEffect } from 'react'
import { fetchCommunities, searchCommunities } from '../services/api'
import '../styles/search-bar.css'

const SearchBar = ({ onSearch, onClear, onCommunitySelect }) => {
  const [query, setQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [searchResults, setSearchResults] = useState([])
  const [allCommunities, setAllCommunities] = useState([])
  const [showResults, setShowResults] = useState(false)
  const searchRef = useRef(null)
  const debounceTimerRef = useRef(null)

  // Fetch all communities on mount
  useEffect(() => {
    const fetchAllCommunities = async () => {
      const { data, error } = await fetchCommunities()
      if (error) {
        console.error('Failed to fetch communities:', error)
        setAllCommunities([])
      } else {
        setAllCommunities(Array.isArray(data) ? data : [])
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
    const { data, error } = await searchCommunities(query)
    if (error) {
      console.error('Search failed:', error)
      setSearchResults([])
      onSearch([], query)
    } else {
      setSearchResults(Array.isArray(data) ? data : [])
      setShowResults(true)
      onSearch(Array.isArray(data) ? data : [], query)
    }
    setIsSearching(false)
  }

  const handleInputChange = (e) => {
    const value = e.target.value
    setQuery(value)

    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    // Handle empty input immediately
    if (value.trim().length === 0) {
      setSearchResults([])
      setShowResults(false)
      onClear()
      return
    }

    // Show loading state immediately
    if (value.trim().length >= 2) {
      setIsSearching(true)
    }

    // Debounce API call (300ms delay)
    debounceTimerRef.current = setTimeout(async () => {
      if (value.trim().length >= 2) {
        const { data, error } = await searchCommunities(value)
        if (error) {
          console.error('Search failed:', error)
          setSearchResults([])
        } else {
          setSearchResults(data)
          setShowResults(true)
          onSearch(data, value)
        }
        setIsSearching(false)
      } else {
        setSearchResults([])
        setShowResults(false)
        setIsSearching(false)
      }
    }, 300)
  }

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [])

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
