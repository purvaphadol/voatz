import React from 'react';
import ReactDOM from 'react-dom';
import { act } from 'react-dom/test-utils';
import VoterRegistrations from './VoterRegistrations';
import { voterRegistrationsAPI, electionsAPI, votersAPI } from '../../../services/api';
import { usePermissions } from '../../../contexts/PermissionContext';

// Mock API and permission context
jest.mock('../../../services/api', () => ({
  voterRegistrationsAPI: {
    getAll: jest.fn(),
    getStats: jest.fn(),
    reject: jest.fn(),
  },
  electionsAPI: {
    getAll: jest.fn(),
  },
  votersAPI: {
    getAll: jest.fn(),
  },
}));

jest.mock('../../../contexts/PermissionContext', () => ({
  usePermissions: jest.fn(),
}));

jest.mock('../../../utils/swal', () => ({
  showErrorAlert: jest.fn(),
}));

// Mock @mui/x-data-grid to cleanly render rows and action items in jsdom
jest.mock('@mui/x-data-grid', () => {
  const actual = jest.requireActual('@mui/x-data-grid');
  return {
    ...actual,
    DataGrid: (props) => {
      return (
        <div data-testid="mock-datagrid">
          {props.rows && props.rows.map((row) => (
            <div key={row.id} data-testid={`row-${row.id}`}>
              <span data-testid="row-status">{row.status}</span>
              {props.columns && props.columns.map((col) => {
                if (col.getActions) {
                  const actions = col.getActions({ row });
                  return (
                    <div key={col.field} data-testid="row-actions">
                      {actions}
                    </div>
                  );
                }
                return null;
              })}
            </div>
          ))}
        </div>
      );
    },
    GridActionsCellItem: ({ icon, label, onClick, ...rest }) => (
      <button data-testid={`action-${label}`} aria-label={label} title={label} onClick={onClick} {...rest}>
        {icon}
        {label}
      </button>
    ),
  };
});

describe('VoterRegistrations Component - Item 6 Behavior Test', () => {
  let container;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    jest.clearAllMocks();
    usePermissions.mockReturnValue({
      hasPermission: (module, action) => true,
    });
    electionsAPI.getAll.mockImplementation(() => Promise.resolve({ data: { data: [] } }));
    votersAPI.getAll.mockImplementation(() => Promise.resolve({ data: { data: [] } }));
    voterRegistrationsAPI.getStats.mockImplementation(() => Promise.resolve({
      data: { total_registrations: 1, pending_registrations: 1, approved_registrations: 0, approval_rate: 0 }
    }));
  });

  afterEach(() => {
    if (container) {
      ReactDOM.unmountComponentAtNode(container);
      document.body.removeChild(container);
      container = null;
    }
  });

  const flush = async () => {
    await new Promise((resolve) => setTimeout(resolve, 100));
  };

  test('renders pending row, confirms no Delete action renders, and clicks Reject action opening dialog without throwing', async () => {
    voterRegistrationsAPI.getAll.mockImplementation(() => Promise.resolve({
      data: {
        data: [
          {
            id: 101,
            voter_id: 1,
            election_id: 1,
            status: 'pending',
            preferred_language: 'en',
            registered_at: '2026-08-01T00:00:00Z',
          },
        ],
      },
    }));

    await act(async () => {
      ReactDOM.render(<VoterRegistrations />, container);
    });
    await act(async () => {
      await flush();
    });

    // 1. Renders VoterRegistrations.js with a row in pending state
    const statusSpan = container.querySelector('[data-testid="row-status"]');
    expect(statusSpan).not.toBeNull();
    expect(statusSpan.textContent).toBe('pending');

    // 2. Confirms no Delete action renders in that row or anywhere on page
    const deleteButton = container.querySelector('[aria-label="Delete"], [data-testid="action-Delete"]');
    expect(deleteButton).toBeNull();
    expect(container.textContent).not.toContain('Delete Registration');

    // 3. Clicks the Reject action and confirms handleReject fires / reject dialog opens without throwing
    const rejectButton = container.querySelector('[aria-label="Reject"], [data-testid="action-Reject"]');
    expect(rejectButton).not.toBeNull();

    await act(async () => {
      rejectButton.click();
    });
    await act(async () => {
      await flush();
    });

    // Verify rejection dialog title is shown in document body (MUI Dialog renders via Portal)
    expect(document.body.textContent).toContain('Reject Registration');
  });

  test('renders approved row, confirms no Delete action renders, and clicks Reject action opening dialog without throwing', async () => {
    voterRegistrationsAPI.getAll.mockImplementation(() => Promise.resolve({
      data: {
        data: [
          {
            id: 102,
            voter_id: 2,
            election_id: 1,
            status: 'approved',
            preferred_language: 'en',
            registered_at: '2026-08-01T00:00:00Z',
          },
        ],
      },
    }));

    await act(async () => {
      ReactDOM.render(<VoterRegistrations />, container);
    });
    await act(async () => {
      await flush();
    });

    // 1. Renders VoterRegistrations.js with a row in approved state
    const statusSpan = container.querySelector('[data-testid="row-status"]');
    expect(statusSpan).not.toBeNull();
    expect(statusSpan.textContent).toBe('approved');

    // 2. Confirms no Delete action renders in that row
    const deleteButton = container.querySelector('[aria-label="Delete"], [data-testid="action-Delete"]');
    expect(deleteButton).toBeNull();

    // 3. Clicks the Reject action and confirms handleReject fires / reject dialog opens without throwing
    const rejectButton = container.querySelector('[aria-label="Reject"], [data-testid="action-Reject"]');
    expect(rejectButton).not.toBeNull();

    await act(async () => {
      rejectButton.click();
    });
    await act(async () => {
      await flush();
    });

    // Verify rejection dialog title is shown in document body
    expect(document.body.textContent).toContain('Reject Registration');
  });
});
