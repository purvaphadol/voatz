import Swal from 'sweetalert2';
import withReactContent from 'sweetalert2-react-content';

const MySwal = withReactContent(Swal);

/**
 * Show a sleek confirmation dialog returning a Promise<boolean>
 */
export const showConfirmDialog = async ({
  title = 'Are you sure?',
  text = 'This action cannot be easily reversed.',
  icon = 'warning',
  confirmButtonText = 'Yes, proceed',
  cancelButtonText = 'Cancel',
  confirmButtonColor = '#d33',
  cancelButtonColor = '#3085d6',
} = {}) => {
  const result = await MySwal.fire({
    title,
    text,
    icon,
    showCancelButton: true,
    confirmButtonText,
    cancelButtonText,
    confirmButtonColor,
    cancelButtonColor,
    reverseButtons: true,
    customClass: {
      confirmButton: 'MuiButton-root MuiButton-contained',
      cancelButton: 'MuiButton-root MuiButton-outlined',
    },
  });

  return result.isConfirmed;
};

/**
 * Quick helper for delete confirmation
 */
export const showDeleteConfirm = async (itemDescription = 'this item') => {
  return showConfirmDialog({
    title: 'Confirm Deletion',
    text: `Are you sure you want to delete ${itemDescription}?`,
    icon: 'warning',
    confirmButtonText: 'Yes, delete it',
    confirmButtonColor: '#d32f2f',
  });
};

/**
 * Quick helper for force delete confirmation
 */
export const showForceDeleteConfirm = async ({
  title = 'Active Dependencies Detected',
  errorText = 'Cannot delete item because active dependencies exist.',
  confirmMessage = 'Are you sure you want to force delete this item and all associated data?',
} = {}) => {
  const result = await MySwal.fire({
    title,
    html: `
      <div style="text-align: left; font-size: 14px; color: #374151;">
        <div style="background-color: #fee2e2; border-left: 4px solid #ef4444; padding: 12px; border-radius: 4px; margin-bottom: 16px; color: #991b1b; font-weight: 500;">
          ${errorText}
        </div>
        <p style="margin: 0; font-weight: 500;">${confirmMessage}</p>
      </div>
    `,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Force Delete',
    cancelButtonText: 'Cancel',
    confirmButtonColor: '#d32f2f',
    cancelButtonColor: '#757575',
    reverseButtons: true,
  });

  return result.isConfirmed;
};

/**
 * Quick helper for success toast
 */
export const showSuccessToast = (title = 'Success!') => {
  MySwal.fire({
    icon: 'success',
    title,
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: 3000,
    timerProgressBar: true,
  });
};

/**
 * Quick helper for success modal alert
 */
export const showSuccessAlert = (message = 'Operation completed successfully.', title = 'Success') => {
  return MySwal.fire({
    icon: 'success',
    title,
    text: message,
    confirmButtonColor: '#1976d2',
  });
};

/**
 * Quick helper for error alert
 */
export const showErrorAlert = (message = 'An unexpected error occurred.') => {
  MySwal.fire({
    icon: 'error',
    title: 'Error',
    text: message,
    confirmButtonColor: '#1976d2',
  });
};

export default MySwal;
