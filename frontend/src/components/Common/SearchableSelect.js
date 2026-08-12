import React from 'react';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';

const SearchableSelect = ({
  options = [],
  getOptionLabel = (option) => (option ? (option.name || option.label || '') : ''),
  getOptionValue = (option) => (option && option.id !== undefined ? option.id : (option ? option.value : '')),
  value,
  onChange,
  label,
  placeholder,
  disabled = false,
  fullWidth = true,
  size,
  margin = "none",
  sx = {},
  allOptionLabel = null, // e.g. "All Companies" or "None (No Department)"
  allOptionValue = "",
  helperText = "",
  error = false,
}) => {
  // Safe helper to derive a display label without ever outputting 'undefined' or throwing errors
  const safeGetOptionLabel = (opt) => {
    if (opt === null || opt === undefined) return '';
    if (opt.isAllOption) return opt.name || opt.label || '';
    try {
      const lbl = getOptionLabel(opt);
      if (lbl === null || lbl === undefined || lbl === 'undefined') return '';
      return String(lbl);
    } catch (e) {
      return '';
    }
  };

  // Build items array, filtering out null/undefined options
  let items = options.filter(opt => opt !== null && opt !== undefined);

  // Sort options alphabetically by display label (case-insensitive)
  items.sort((a, b) => {
    const labelA = safeGetOptionLabel(a);
    const labelB = safeGetOptionLabel(b);
    return labelA.localeCompare(labelB, undefined, { sensitivity: 'base' });
  });

  if (allOptionLabel !== null) {
    items.unshift({
      id: allOptionValue,
      name: allOptionLabel,
      label: allOptionLabel,
      value: allOptionValue,
      isAllOption: true
    });
  }

  // Explicitly treat null, undefined, and 'undefined' as empty string selection
  const normValue = (value === null || value === undefined || value === 'undefined') ? '' : String(value);

  const selectedOption = items.find(opt => {
    const rawVal = getOptionValue(opt);
    const normOptVal = (rawVal === null || rawVal === undefined || rawVal === 'undefined') ? '' : String(rawVal);
    return normOptVal === normValue;
  }) || null;

  return (
    <Autocomplete
      options={items}
      getOptionLabel={(opt) => safeGetOptionLabel(opt)}
      isOptionEqualToValue={(option, val) => {
        if (!option || !val) return false;
        const rawOpt = getOptionValue(option);
        const rawVal = getOptionValue(val);
        const normOpt = (rawOpt === null || rawOpt === undefined || rawOpt === 'undefined') ? '' : String(rawOpt);
        const normVal = (rawVal === null || rawVal === undefined || rawVal === 'undefined') ? '' : String(rawVal);
        return normOpt === normVal;
      }}
      value={selectedOption}
      onChange={(event, newValue) => {
        const val = newValue ? getOptionValue(newValue) : '';
        const finalVal = (val === null || val === undefined || val === 'undefined') ? '' : val;
        if (onChange) {
          onChange({ target: { value: finalVal } });
        }
      }}
      disabled={disabled}
      fullWidth={fullWidth}
      size={size}
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          placeholder={placeholder}
          margin={margin}
          variant="outlined"
          helperText={helperText}
          error={error}
        />
      )}
      sx={{
        '& .MuiOutlinedInput-root': {
          minHeight: '56px',
          height: '56px',
          paddingTop: '9px !important',
          paddingBottom: '9px !important',
          '& .MuiAutocomplete-input': {
            padding: '7.5px 4px !important',
          },
        },
        ...sx
      }}
    />
  );
};

export default SearchableSelect;
