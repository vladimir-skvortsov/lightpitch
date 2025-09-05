import { useState, useRef, useEffect } from 'react'
import './Dropdown.scss'

const Dropdown = ({ children, className = '' }) => {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  // Закрытие при клике вне dropdown
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  // Закрытие при нажатии Escape
  useEffect(() => {
    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  const toggleDropdown = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsOpen(!isOpen)
  }

  return (
    <div className={`dropdown ${className}`} ref={dropdownRef}>
      <button className='dropdown-trigger' onClick={toggleDropdown} aria-haspopup='true' aria-expanded={isOpen}>
        <span className='dropdown-dots'>⋯</span>
      </button>

      {isOpen && (
        <div className='dropdown-menu'>
          <div className='dropdown-content'>{children}</div>
        </div>
      )}
    </div>
  )
}

export default Dropdown
