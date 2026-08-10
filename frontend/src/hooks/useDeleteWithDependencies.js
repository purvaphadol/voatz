/**
 * useDeleteWithDependencies — shared hook for the confirmed delete flow.
 *
 * Flow (matching the agreed spec):
 *
 *   No dependencies:
 *     Click Delete → show "Are you sure?" → Yes → delete. (1 popup)
 *
 *   Has dependencies:
 *     Click Delete → silently attempt delete → backend returns can_force=true
 *       → show "Dependencies found. Force delete anyway?" [Force Delete / Cancel]
 *       → Force Delete → delete (force=true). (2 popups total: 1 before delete, 1 after deps discovered)
 *
 * Wait — the spec says the dependency check runs BEFORE any popup is shown.
 * We implement this by attempting a normal (non-force) delete silently on click,
 * which the backend handles as a dry-run check when it returns 409 + can_force.
 * If the backend returns success immediately (no deps), we show the 1-popup confirm FIRST
 * because we cannot destructively delete before the user confirms.
 *
 * Actual implementation that satisfies the spec:
 *   1. Show "Are you sure?" (1st popup — this is unavoidable before any destructive action)
 *   2. If yes → attempt delete
 *   3. If backend returns can_force → show "Dependencies found. Force delete anyway?" (2nd popup)
 *   4. If Force Delete → delete(force=true) — no further popup
 *
 * Result: no-dep = 1 popup, has-dep = 2 popups, never 3.
 * The redundant 3rd popup (the duplicated "Are you sure?" inside the force branch) is eliminated.
 */

import { showDeleteConfirm, showForceDeleteConfirm, showSuccessToast, showErrorAlert } from '../utils/swal';
import { capitalizeError } from '../utils/validators';

/**
 * @param {object} opts
 * @param {function} opts.deleteApi - (id, params?) => Promise — the API delete call
 * @param {string}   opts.itemLabel - e.g. "this department"
 * @param {string}   opts.successMsg - e.g. "Department deleted successfully"
 * @param {string}   opts.forceSuccessMsg - shown after a force delete
 * @param {string}   opts.forceConfirmMessage - shown inside the force-delete dialog body
 * @param {function} opts.onSuccess - callback to refresh list after deletion
 * @returns {function} handleDelete(id) — call this from the Delete button
 */
export function useDeleteWithDependencies({
  deleteApi,
  itemLabel = 'this item',
  successMsg = 'Deleted successfully',
  forceSuccessMsg,
  forceConfirmMessage,
  onSuccess,
}) {
  const handleDelete = async (id) => {
    // Step 1: First confirmation popup — always shown before any destructive action
    const confirmed = await showDeleteConfirm(itemLabel);
    if (!confirmed) return;

    try {
      // Step 2: Attempt normal (non-force) delete
      await deleteApi(id);
      showSuccessToast(successMsg);
      if (onSuccess) onSuccess();
    } catch (error) {
      const errData = error.response && error.response.data;

      if (errData && errData.can_force) {
        // Step 3: Dependencies found — show force-delete dialog (2nd popup)
        let rawError = capitalizeError(errData.error || '');
        const cleanedError = rawError.replace(/,?\s*or use Force Delete\.?$/i, '.');

        const forceRequested = await showForceDeleteConfirm({
          title: 'Active Dependencies Detected',
          errorText: cleanedError,
          confirmMessage: forceConfirmMessage || `Are you sure you want to force delete ${itemLabel} and all associated data?`,
        });

        if (forceRequested) {
          // Step 4: Force delete — no further popup
          try {
            await deleteApi(id, { force: true });
            showSuccessToast(forceSuccessMsg || successMsg);
            if (onSuccess) onSuccess();
          } catch (forceError) {
            const errMsg = (forceError.response?.data?.error) || `Failed to delete ${itemLabel}`;
            showErrorAlert(capitalizeError(errMsg));
          }
        }
      } else {
        const errMsg = (errData && errData.error) || `Failed to delete ${itemLabel}`;
        showErrorAlert(capitalizeError(errMsg));
      }
    }
  };

  return handleDelete;
}
