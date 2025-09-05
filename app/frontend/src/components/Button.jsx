import { forwardRef } from 'react'
import './Button.scss'

const Button = forwardRef(
  (
    {
      as: Component = 'button',
      variant = 'default',
      size = 'medium',
      disabled = false,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    const baseClass = 'btn'
    const variantClass = `btn--${variant}`
    const sizeClass = `btn--${size}`
    const disabledClass = disabled ? 'btn--disabled' : ''

    const buttonClass = [baseClass, variantClass, sizeClass, disabledClass, className].filter(Boolean).join(' ')

    const componentProps = Component === 'button' ? { disabled, ...props } : props

    return (
      <Component ref={ref} className={buttonClass} {...componentProps}>
        {children}
      </Component>
    )
  }
)

Button.displayName = 'Button'

export default Button
