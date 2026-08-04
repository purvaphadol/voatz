/**
 * Frontend Validation Helpers
 */

/**
 * Validates that text is not empty and is not purely numeric (must contain at least one letter).
 * @param {string} value
 * @param {number} minLength
 * @param {number} maxLength
 * @returns {string|null} Error message or null if valid.
 */
export const validateNonNumericText = (value, fieldName = 'Field', minLength = 2, maxLength = 100) => {
  if (!value || typeof value !== 'string') {
    return `${fieldName} is required`;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return `${fieldName} cannot be empty`;
  }
  if (trimmed.length < minLength) {
    return `${fieldName} must be at least ${minLength} characters`;
  }
  if (trimmed.length > maxLength) {
    return `${fieldName} cannot exceed ${maxLength} characters`;
  }
  if (/^\d+$/.test(trimmed)) {
    return `${fieldName} cannot consist solely of numbers`;
  }
  if (!/[a-zA-Z]/.test(trimmed)) {
    return `${fieldName} must contain at least one letter`;
  }
  return null;
};

/**
 * Validates RFC email format.
 * @param {string} email
 * @returns {string|null}
 */
export const validateEmail = (email) => {
  if (!email || !email.trim()) {
    return 'Email is required';
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email.trim())) {
    return 'Invalid email address format';
  }
  return null;
};

/**
 * Validates phone / mobile number format.
 * @param {string} phone
 * @returns {string|null}
 */
export const validatePhone = (phone) => {
  if (!phone || !phone.trim()) return null; // Optional
  const trimmed = phone.trim();
  if (trimmed.length < 7 || trimmed.length > 20) {
    return 'Phone number must be between 7 and 20 characters';
  }
  const phoneRegex = /^\+?[0-9\-\s()]{7,20}$/;
  if (!phoneRegex.test(trimmed)) {
    return 'Invalid phone number format';
  }
  return null;
};

/**
 * Validates HTTP/HTTPS URL format.
 * @param {string} url
 * @returns {string|null}
 */
export const validateUrl = (url) => {
  if (!url || !url.trim()) return null; // Optional
  const trimmed = url.trim();
  if (trimmed.startsWith('data:image/')) return null;
  const urlRegex = /^(https?:\/\/)?([\da-z.-]+)\.([a-z.]{2,6})([/\w .-]*)*\/?$/i;
  if (!urlRegex.test(trimmed)) {
    return 'Invalid URL format (must be valid HTTP/HTTPS URL)';
  }
  return null;
};

/**
 * Validates ISO date range.
 * @param {string|Date} startDate
 * @param {string|Date} endDate
 * @returns {string|null}
 */
export const validateDateRange = (startDate, endDate) => {
  if (!startDate || !endDate) {
    return 'Start date and end date are required';
  }
  const start = new Date(startDate);
  const end = new Date(endDate);
  if (isNaN(start.getTime()) || isNaN(end.getTime())) {
    return 'Invalid date format';
  }
  if (end <= start) {
    return 'End date must be strictly after start date';
  }
  return null;
};
