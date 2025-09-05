import { useState, useRef, useEffect, cloneElement, Children } from 'react'
import './Dropdown.scss'

const Dropdown = ({ trigger, children, className = '' }) => {
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

  const handleItemClick = () => {
    setIsOpen(false)
  }

  return (
    <div className={`dropdown ${className}`} ref={dropdownRef}>
      {cloneElement(trigger, {
        onClick: toggleDropdown,
        'aria-haspopup': 'true',
        'aria-expanded': isOpen,
        className: `dropdown-trigger ${trigger.props.className || ''}`.trim(),
      })}

      {isOpen && (
        <div className='dropdown-menu'>
          <div className='dropdown-content'>
            {Children.map(children, (child) =>
              cloneElement(child, {
                onClick: (e) => {
                  if (child.props.onClick) {
                    child.props.onClick(e)
                  }
                  handleItemClick()
                },
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Dropdown
